import logging
import re

from memory_validator import MemoryValidator
from normalizer import Normalizer


logger = logging.getLogger(__name__)


PREFERENCE_PATTERNS = [
    re.compile(r"\bich bevorzuge\b(?P<value>.+)", re.I),
    re.compile(r"\bich mag\b(?P<value>.+)", re.I),
    re.compile(r"\bich liebe\b(?P<value>.+)", re.I),
    re.compile(r"\bmerke dir\b(?P<value>.+)", re.I),
    re.compile(r"\bspeichere\b(?P<value>.+)", re.I),
    re.compile(r"\bnotiere\b(?P<value>.+)", re.I),
    re.compile(r"\bich suche regelmäßig\b(?P<value>.+)", re.I),
]


class ResearchMemoryIntegrator:

    def __init__(self, memory, normalizer=None, validator=None):
        self.memory = memory
        self.normalizer = normalizer or Normalizer()
        self.validator = validator or MemoryValidator()


    def _normalize_text(self, value):
        return " ".join(str(value).strip().split())


    def _get_result_text(self, research_result):
        if research_result is None:
            return ""
        if hasattr(research_result, "summary"):
            return self._normalize_text(getattr(research_result, "summary", ""))
        if isinstance(research_result, dict):
            return self._normalize_text(research_result.get("summary") or research_result.get("answer", ""))
        return self._normalize_text(str(research_result))


    def _detect_preference(self, query, research_result):
        combined = f"{query}\n{self._get_result_text(research_result)}".strip()
        for pattern in PREFERENCE_PATTERNS:
            match = pattern.search(combined)
            if match:
                value = self._normalize_text(match.group("value"))
                if value:
                    return value.lstrip(" ,:;-")
        return ""


    def should_store(self, query, research_result, explicit_request=False):
        if explicit_request:
            return True
        if self._detect_preference(query, research_result):
            return True
        result_text = self._get_result_text(research_result).casefold()
        if any(token in result_text for token in ("bevorzugt", "prefers", "preference", "favorite", "favorit")):
            return True
        return False


    def build_candidates(self, query, research_result, explicit_request=False):
        candidates = []
        preference = self._detect_preference(query, research_result)
        result_text = self._get_result_text(research_result)

        if preference:
            candidates.append(
                {
                    "category": "preferences",
                    "key": "research_preference",
                    "value": preference,
                    "importance": 7,
                    "confidence": 0.9,
                    "kind": "fact",
                }
            )

        if explicit_request and result_text:
            candidates.append(
                {
                    "category": "research_notes",
                    "key": "explicit_research_note",
                    "value": result_text,
                    "importance": 6,
                    "confidence": 0.8,
                    "kind": "summary",
                    "topic": "research_note",
                }
            )

        return candidates


    def persist(self, query, research_result, explicit_request=False):
        if not self.memory or not self.should_store(query, research_result, explicit_request=explicit_request):
            return []

        candidate_items = self.build_candidates(query, research_result, explicit_request=explicit_request)
        saved = []
        result_confidence = 0.7
        if hasattr(research_result, "confidence"):
            try:
                result_confidence = float(getattr(research_result, "confidence", 0.7))
            except Exception:
                result_confidence = 0.7
        elif isinstance(research_result, dict):
            try:
                result_confidence = float(research_result.get("confidence", 0.7))
            except Exception:
                result_confidence = 0.7

        for candidate in candidate_items:
            kind = candidate.pop("kind", "fact")
            if kind == "fact":
                fact = self.normalizer.normalize_fact(candidate)
                validation = self.validator.validate(fact, self._get_result_text(research_result))
                if validation and validation.get("approved", False):
                    importance = max(candidate.get("importance", 5), validation.get("importance", 5))
                    confidence = min(1.0, max(result_confidence, validation.get("confidence", 0.75)))
                    self.memory.save_fact(
                        key=fact["key"],
                        value=fact["value"],
                        category=fact.get("category", "general"),
                        importance=importance,
                        confidence=confidence,
                    )
                    saved.append({"kind": "fact", "key": fact["key"], "value": fact["value"], "confidence": confidence})
            else:
                topic = candidate.pop("topic", "research_note")
                summary = self.normalizer.normalize_summary(
                    {
                        "topic": topic,
                        "summary": candidate.get("value", ""),
                        "importance": candidate.get("importance", 5),
                        "confidence": candidate.get("confidence", result_confidence),
                    }
                )
                if summary.get("topic") and summary.get("summary"):
                    self.memory.save_summary(
                        summary["topic"],
                        summary["summary"],
                        importance=summary.get("importance", 5),
                        confidence=summary.get("confidence", result_confidence),
                    )
                    saved.append({"kind": "summary", "topic": summary["topic"], "confidence": summary.get("confidence", result_confidence)})

        return saved
