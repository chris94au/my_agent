import json
import logging
import re

import ollama


logger = logging.getLogger(__name__)


DEFAULT_FACT_LIMIT = 8


class ResearchExtractor:

    def __init__(self, model="qwen2.5:7b"):
        self.model = model


    def _normalize_source(self, source):
        if hasattr(source, "__dict__"):
            source = source.__dict__
        return dict(source or {})


    def _build_prompt(self, query, source):
        source = self._normalize_source(source)
        content = str(source.get("content", ""))
        excerpt = content[:6000]
        return f"""
Du bist ein Informations-Extractor für Research-Aufgaben.

Extrahiere ausschließlich belegte Fakten aus der Quelle.
Erfinde keine Werte.
Wenn ein Feld nicht belegt ist, lasse es leer oder verwende null.

Benutzerfrage:
{query}

Quelle:
- URL: {source.get('url', '')}
- Titel: {source.get('title', '')}
- Inhalt:
{excerpt}

Antworte ausschließlich als JSON mit diesem Schema:
{{
  "summary": "kurze Zusammenfassung der Quelle",
  "confidence": 0.0,
  "facts": [
    {{
      "name": "Name oder Objekt",
      "location": "Ort oder leer",
      "rating": 4.8,
      "category": "Kategorie",
      "source": "Quell-URL",
      "evidence": "direkter Belegtext",
      "confidence": 0.0
    }}
  ]
}}
"""


    def _extract_json(self, text):
        if not text:
            return None

        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )
        if not match:
            return None

        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None


    def _validate_fact(self, fact, default_source_url):
        if not isinstance(fact, dict):
            return None

        name = str(fact.get("name", "")).strip()
        if not name:
            return None

        location = str(fact.get("location", "")).strip()
        category = str(fact.get("category", "")).strip() or "research_fact"
        source = str(fact.get("source", "")).strip() or default_source_url
        evidence = str(fact.get("evidence", "")).strip()

        rating = fact.get("rating", None)
        if rating in ("", None):
            rating = None
        else:
            try:
                rating = float(rating)
            except Exception:
                rating = None

        confidence = fact.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.5

        return {
            "name": name,
            "location": location,
            "rating": rating,
            "category": category,
            "source": source,
            "evidence": evidence,
            "confidence": max(0.0, min(1.0, confidence)),
        }


    def _fallback_extract(self, source):
        source = self._normalize_source(source)
        title = str(source.get("title", "")).strip()
        content = str(source.get("content", "")).strip()
        excerpt = content[:500]

        facts = []
        if title or excerpt:
            facts.append(
                {
                    "name": title or source.get("url", ""),
                    "location": "",
                    "rating": None,
                    "category": "source_excerpt",
                    "source": source.get("url", ""),
                    "evidence": excerpt,
                    "confidence": 0.45,
                }
            )

        return {
            "status": "ok",
            "summary": title or "Fallback-Extraktion",
            "confidence": 0.45,
            "facts": facts,
            "validated": True,
            "warnings": ["Fallback extraction used"],
            "source": source.get("url", ""),
        }


    def extract(self, query, source):
        source = self._normalize_source(source)
        prompt = self._build_prompt(query, source)

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            )
            raw_text = response["message"]["content"]
            extracted = self._extract_json(raw_text)
            if extracted is None:
                raise ValueError("Extractor output was not valid JSON")
        except Exception as exc:
            logger.warning("Extractor fallback due to error: %s", exc)
            return self._fallback_extract(source)

        facts = []
        for fact in extracted.get("facts", [])[:DEFAULT_FACT_LIMIT]:
            validated = self._validate_fact(fact, source.get("url", ""))
            if validated is not None:
                facts.append(validated)

        confidence = extracted.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.5

        summary = str(extracted.get("summary", "")).strip() or str(source.get("title", "")).strip()
        warnings = []
        if not facts:
            warnings.append("No validated facts extracted")

        return {
            "status": "ok",
            "summary": summary,
            "confidence": max(0.0, min(1.0, confidence)),
            "facts": facts,
            "validated": True,
            "warnings": warnings,
            "source": source.get("url", ""),
            "raw": extracted,
        }
