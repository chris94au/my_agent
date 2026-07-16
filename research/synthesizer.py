import logging
from collections import defaultdict


logger = logging.getLogger(__name__)


class ResearchSynthesizer:

    def __init__(self, model="qwen2.5:7b", citation_tracker=None):
        self.model = model
        self.citation_tracker = citation_tracker


    def _normalize_source(self, source):
        if hasattr(source, "__dict__"):
            source = source.__dict__
        return dict(source or {})


    def _source_weight(self, source):
        score = float(source.get("rank_score", source.get("score", 0.5)) or 0.5)
        reliability = float(source.get("reliability", 0.5) or 0.5)
        relevance = float(source.get("relevance", 0.5) or 0.5)
        confidence = float(source.get("confidence", 0.5) or 0.5)
        return max(0.05, min(1.0, 0.4 * score + 0.25 * reliability + 0.2 * relevance + 0.15 * confidence))


    def _fact_key(self, fact):
        return (
            str(fact.get("name", "")).strip().casefold(),
            str(fact.get("location", "")).strip().casefold(),
            str(fact.get("category", "")).strip().casefold(),
        )


    def _merge_facts(self, sources):
        groups = defaultdict(list)
        for source in sources:
            source_data = self._normalize_source(source)
            facts = source_data.get("extracted", {}).get("facts", []) if isinstance(source_data.get("extracted"), dict) else []
            for fact in facts:
                if not isinstance(fact, dict):
                    continue
                groups[self._fact_key(fact)].append((source_data, fact))
        return groups


    def synthesize(self, query, memory_context, sources):
        normalized_sources = [self._normalize_source(source) for source in sources or []]
        source_urls = [source.get("url", "") for source in normalized_sources if source.get("url")]
        groups = self._merge_facts(normalized_sources)

        claims = []
        contradictions = []
        uncertainties = []
        citations = []
        weighted_confidence = 0.0
        total_weight = 0.0

        if memory_context:
            uncertainties.append("Vorwissen wurde zur Einordnung verwendet.")

        for key, items in groups.items():
            if not items:
                continue

            ranked_items = sorted(
                items,
                key=lambda pair: self._source_weight(pair[0]) * max(0.1, float(pair[1].get("confidence", 0.5) or 0.5)),
                reverse=True,
            )
            primary_source, primary_fact = ranked_items[0]
            primary_weight = self._source_weight(primary_source)
            primary_confidence = float(primary_fact.get("confidence", 0.5) or 0.5)
            weighted_confidence += primary_weight * primary_confidence
            total_weight += primary_weight

            claim = {
                "name": primary_fact.get("name", ""),
                "location": primary_fact.get("location", ""),
                "rating": primary_fact.get("rating", None),
                "category": primary_fact.get("category", ""),
                "source": primary_fact.get("source") or primary_source.get("url", ""),
                "confidence": round(min(1.0, max(0.0, primary_confidence)), 2),
                "evidence": primary_fact.get("evidence", ""),
            }
            claims.append(claim)
            citations.append(
                {
                    "claim": claim["name"] or claim["evidence"],
                    "source": claim["source"],
                    "timestamp": None,
                    "confidence": claim["confidence"],
                }
            )

            if len(ranked_items) > 1:
                competing_values = []
                for source_data, fact in ranked_items[1:]:
                    rating = fact.get("rating")
                    competing_values.append(
                        {
                            "source": source_data.get("url", ""),
                            "rating": rating,
                            "name": fact.get("name", ""),
                            "confidence": fact.get("confidence", 0.5),
                        }
                    )
                if competing_values:
                    ratings = [item[1].get("rating") for item in ranked_items if item[1].get("rating") is not None]
                    if len(set(ratings)) > 1:
                        contradictions.append(
                            {
                                "claim": claim["name"],
                                "sources": [item["source"] for item in competing_values] + [claim["source"]],
                            }
                        )
                    else:
                        uncertainties.append(
                            f"{claim['name']} wird von mehreren Quellen mit unterschiedlicher Detailtiefe beschrieben."
                        )

        if not claims:
            summary = "Keine belastbaren Fakten aus den Quellen extrahiert."
            confidence = 0.35
        else:
            bullets = []
            for claim in claims:
                line = claim["name"]
                if claim.get("location"):
                    line += f" in {claim['location']}"
                if claim.get("rating") is not None:
                    line += f" ({claim['rating']}/5)"
                line += f" — Quelle: {claim['source']}"
                bullets.append(line)
            summary = "\n".join(bullets)
            confidence = weighted_confidence / total_weight if total_weight else 0.5
            if contradictions:
                summary += "\n\nWidersprüche wurden erkannt und markiert."
            if uncertainties:
                summary += "\n\nUnsicherheiten: " + "; ".join(dict.fromkeys(uncertainties))

        if self.citation_tracker is not None:
            for citation in citations:
                self.citation_tracker.record(
                    claim=citation["claim"],
                    source=citation["source"],
                    confidence=citation["confidence"],
                    metadata={"query": query},
                )

        return {
            "answer": summary,
            "summary": summary,
            "sources_used": source_urls,
            "confidence": round(min(1.0, max(0.0, confidence)), 2),
            "claims": claims,
            "contradictions": contradictions,
            "uncertainties": uncertainties,
            "citations": citations,
            "warnings": [],
        }
