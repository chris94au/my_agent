import json
import logging
from dataclasses import dataclass, field

from tools.internet_research import web_search
from tools.web_fetch import fetch_url

from .citations import CitationTracker
from .extractor import ResearchExtractor
from .html_parser import extract_html_content
from .memory_integration import ResearchMemoryIntegrator
from .source_ranker import SourceRanker
from .synthesizer import ResearchSynthesizer


logger = logging.getLogger(__name__)


@dataclass
class ResearchSource:
    title: str
    url: str
    snippet: str = ""
    rank_score: float = 0.0
    reliability: float = 0.5
    relevance: float = 0.5
    fetched: dict = field(default_factory=dict)
    extracted: dict = field(default_factory=dict)


@dataclass
class ResearchResult:
    query: str
    summary: str
    sources_used: list[str] = field(default_factory=list)
    sources: list[ResearchSource] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    confidence: float = 0.5
    research_context: str = ""
    citation_context: str = ""
    existing_knowledge: str = ""
    warnings: list[str] = field(default_factory=list)
    memory_actions: list[dict] = field(default_factory=list)


class ResearchPipeline:

    def __init__(self, model="qwen2.5:7b", searcher=web_search, fetcher=fetch_url, source_ranker=None, extractor=None, synthesizer=None, citation_tracker=None, memory=None):
        self.model = model
        self.searcher = searcher
        self.fetcher = fetcher
        self.source_ranker = source_ranker or SourceRanker()
        self.extractor = extractor or ResearchExtractor(model=model)
        self.citation_tracker = citation_tracker or CitationTracker()
        self.synthesizer = synthesizer or ResearchSynthesizer(
            model=model,
            citation_tracker=self.citation_tracker
        )
        self.memory = memory
        self.memory_integrator = ResearchMemoryIntegrator(memory) if memory is not None else None


    def _parse_json(self, payload, fallback=None):
        if isinstance(payload, dict):
            return payload

        if not payload:
            return fallback or {}

        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return fallback or {}


    def _search(self, query, max_results=5):
        logger.info("Research search for query: %s", query)
        raw = self.searcher({"query": query, "max_results": max_results})
        parsed = self._parse_json(raw, fallback={"results": []})
        results = parsed.get("results", []) if isinstance(parsed, dict) else []
        return results


    def _select_sources(self, query, search_results, limit=5):
        sources = []
        for item in search_results[: limit * 3]:
            if not isinstance(item, dict):
                continue
            source = ResearchSource(
                title=str(item.get("title", "")).strip(),
                url=str(item.get("url", "")).strip(),
                snippet=str(item.get("snippet", "")).strip(),
            )
            if source.url.startswith(("http://", "https://")):
                sources.append(source)

        ranked = self.source_ranker.rank_sources(query, [source.__dict__ for source in sources], limit=limit)
        ranked_sources = []
        for item in ranked:
            ranked_source = ResearchSource(
                title=str(item.get("title", "")).strip(),
                url=str(item.get("url", "")).strip(),
                snippet=str(item.get("snippet", "")).strip(),
                rank_score=float(item.get("score", 0.0) or 0.0),
                reliability=float(item.get("reliability", 0.5) or 0.5),
                relevance=float(item.get("relevance", 0.5) or 0.5),
            )
            ranked_sources.append(ranked_source)
        return ranked_sources


    def _fetch_sources(self, sources):
        fetched = []
        for source in sources:
            logger.info("Fetching research source: %s", source.url)
            payload = self.fetcher({"url": source.url})
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {"status": "error", "error": payload}
            source.fetched = payload if isinstance(payload, dict) else {"status": "error", "error": "invalid payload"}
            if source.fetched.get("status") == "ok":
                content = str(source.fetched.get("content", ""))
                if "<" in content and ">" in content:
                    title, content = extract_html_content(content)
                    if title and not source.fetched.get("title"):
                        source.fetched["title"] = title
                source.fetched["content"] = content
            fetched.append(source)
        return fetched


    def _extract_from_source(self, query, source):
        if self.extractor is not None:
            extracted = self.extractor.extract(query=query, source=source.fetched)
            source.extracted = extracted if isinstance(extracted, dict) else {"facts": extracted}
            return source.extracted

        content = source.fetched.get("content", "") if isinstance(source.fetched, dict) else ""
        title = source.fetched.get("title", "") if isinstance(source.fetched, dict) else ""
        excerpt = content[:1000]
        source.extracted = {
            "facts": [
                {
                    "name": title or source.title,
                    "location": "",
                    "rating": None,
                    "category": "source_excerpt",
                    "source": source.url,
                    "excerpt": excerpt,
                }
            ] if excerpt else []
        }
        return source.extracted


    def _synthesize(self, query, memory_context, sources):
        if self.synthesizer is not None:
            return self.synthesizer.synthesize(query=query, memory_context=memory_context, sources=[source.__dict__ for source in sources])

        citations = []
        research_lines = []
        confidence_total = 0.0
        used_count = 0

        if memory_context:
            research_lines.append("Bekanntes Vorwissen:")
            research_lines.append(memory_context.strip())
            research_lines.append("")

        research_lines.append("Recherchierte Quellen:")
        for source in sources:
            fetched = source.fetched if isinstance(source.fetched, dict) else {}
            extracted = source.extracted if isinstance(source.extracted, dict) else {}
            content_excerpt = fetched.get("content", "")[:500]
            research_lines.append(
                f"- {source.title or source.url} ({source.url})"
            )
            if fetched.get("title"):
                research_lines.append(f"  Titel: {fetched['title']}")
            if content_excerpt:
                research_lines.append(f"  Inhalt: {content_excerpt}")
            if extracted.get("facts"):
                for fact in extracted["facts"]:
                    claim = fact.get("name") or fact.get("excerpt") or source.title or source.url
                    citation = {
                        "claim": claim,
                        "source": source.url,
                        "timestamp": None,
                        "confidence": min(0.95, max(0.3, source.reliability * 0.6 + source.relevance * 0.4)),
                    }
                    citations.append(citation)
                    research_lines.append(f"  Fakt: {claim}")
                    if fact.get("rating") is not None:
                        research_lines.append(f"  Bewertung: {fact['rating']}")
                    if fact.get("location"):
                        research_lines.append(f"  Ort: {fact['location']}")
                    confidence_total += citation["confidence"]
                    used_count += 1

        if not citations:
            for source in sources:
                citations.append(
                    {
                        "claim": source.title or source.url,
                        "source": source.url,
                        "timestamp": None,
                        "confidence": max(0.3, source.relevance * 0.5 + source.reliability * 0.5),
                    }
                )
                confidence_total += citations[-1]["confidence"]
                used_count += 1

        confidence = confidence_total / used_count if used_count else 0.5
        summary = "\n".join(research_lines).strip()
        return {
            "answer": summary,
            "summary": summary,
            "sources_used": [source.url for source in sources],
            "confidence": round(min(1.0, confidence), 2),
            "citations": citations,
            "warnings": [],
        }


    def run(self, query, memory_context="", limit=5):
        existing_knowledge = memory_context.strip()
        search_results = self._search(query, max_results=max(limit, 5))
        selected_sources = self._select_sources(query, search_results, limit=limit)
        fetched_sources = self._fetch_sources(selected_sources)

        for source in fetched_sources:
            if source.fetched.get("status") == "ok":
                self._extract_from_source(query, source)

        synthesis = self._synthesize(query, existing_knowledge, fetched_sources)
        answer = synthesis.get("answer", "") if isinstance(synthesis, dict) else str(synthesis)
        summary = synthesis.get("summary", answer) if isinstance(synthesis, dict) else answer
        sources_used = synthesis.get("sources_used", [source.url for source in fetched_sources]) if isinstance(synthesis, dict) else [source.url for source in fetched_sources]
        citations = synthesis.get("citations", []) if isinstance(synthesis, dict) else []
        confidence = synthesis.get("confidence", 0.5) if isinstance(synthesis, dict) else 0.5
        warnings = synthesis.get("warnings", []) if isinstance(synthesis, dict) else []
        citation_context = self.citation_tracker.as_context() if self.citation_tracker else ""

        research_context_lines = []
        if existing_knowledge:
            research_context_lines.append("Vorwissen:")
            research_context_lines.append(existing_knowledge)
            research_context_lines.append("")
        research_context_lines.append("Research Summary:")
        research_context_lines.append(summary)
        research_context_lines.append("")
        research_context_lines.append("Sources:")
        for source in fetched_sources:
            research_context_lines.append(f"- {source.url} | score={source.rank_score:.2f} | rel={source.relevance:.2f} | conf={source.reliability:.2f}")
        if citations:
            research_context_lines.append("")
            research_context_lines.append("Citations:")
            for citation in citations:
                research_context_lines.append(
                    f"- {citation.get('claim')} <- {citation.get('source')} (confidence={citation.get('confidence', 0.0):.2f})"
                )
        if warnings:
            research_context_lines.append("")
            research_context_lines.append("Warnings:")
            for warning in warnings:
                research_context_lines.append(f"- {warning}")

        memory_actions = []
        if self.memory_integrator is not None:
            explicit_request = any(
                token in query.casefold()
                for token in ("merke dir", "speichere", "notiere", "remember", "save this", "save that")
            )
            memory_actions = self.memory_integrator.persist(
                query,
                synthesis,
                explicit_request=explicit_request,
            )

        return ResearchResult(
            query=query,
            summary=summary,
            sources_used=sources_used,
            sources=fetched_sources,
            citations=citations,
            confidence=confidence,
            research_context="\n".join(research_context_lines).strip(),
            citation_context=citation_context,
            existing_knowledge=existing_knowledge,
            warnings=warnings,
            memory_actions=memory_actions,
        )
