import logging
import math
import re
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


STOPWORDS = {
    "and", "the", "for", "with", "that", "this", "from", "was", "are",
    "you", "your", "they", "their", "have", "has", "not", "but", "can",
    "will", "about", "into", "what", "when", "where", "who", "why",
    "wie", "und", "der", "die", "das", "mit", "für", "von", "den",
    "dem", "des", "ein", "eine", "einer", "einem", "auf", "im", "in",
    "zu", "ist", "sind", "war", "waren", "nicht", "oder", "auch",
    "dass", "was", "wer", "wo", "wann", "warum", "ohne"
}

DOMAIN_RELIABILITY = {
    "gov": 0.95,
    "edu": 0.92,
    "org": 0.78,
    "wikipedia.org": 0.76,
    "falstaff.com": 0.86,
    "tripadvisor.com": 0.72,
    "google.com": 0.78,
    "yelp.com": 0.74,
    "news.google.com": 0.8,
}



def _normalize_source(source):
    if hasattr(source, "__dict__"):
        source = source.__dict__
    return dict(source or {})



def _tokenize(text):
    return [
        token.lower()
        for token in re.findall(r"[\wÄÖÜäöüß]+", str(text), flags=re.UNICODE)
        if token
    ]



def _domain_reliability(url):
    parsed = urlparse(str(url))
    host = parsed.netloc.lower()
    if not host:
        return 0.45

    for key, value in DOMAIN_RELIABILITY.items():
        if key in host:
            return value

    if host.endswith(".gov"):
        return 0.95
    if host.endswith(".edu"):
        return 0.92
    if host.endswith(".org"):
        return 0.78
    if host.count(".") >= 2:
        return 0.55
    return 0.5



def _freshness_score(source):
    timestamp = str(source.get("published_at") or source.get("updated_at") or source.get("last_seen") or source.get("last_seen_at") or "").strip()
    if not timestamp:
        return 0.5

    try:
        import datetime as _datetime

        parsed = _datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        age_days = max((_datetime.datetime.now(_datetime.timezone.utc) - parsed).total_seconds() / 86400.0, 0.0)
        return max(0.1, min(1.0, math.exp(-age_days / 180.0)))
    except Exception:
        return 0.5



def _relevance_score(query, source):
    keywords = [token for token in _tokenize(query) if token not in STOPWORDS and len(token) > 2]
    haystack = " ".join(
        [
            str(source.get("title", "")),
            str(source.get("snippet", "")),
            str(source.get("content", "")),
        ]
    ).lower()
    if not keywords:
        return 0.5

    matches = sum(1 for keyword in keywords if keyword in haystack)
    coverage = matches / len(keywords)
    phrase_bonus = 0.15 if str(source.get("title", "")).lower().find(keywords[0]) >= 0 else 0.0
    return max(0.05, min(1.0, 0.15 + (0.8 * coverage) + phrase_bonus))



def _completeness_score(source):
    content = str(source.get("content", "") or source.get("snippet", ""))
    length_score = min(len(content) / 1800.0, 1.0)
    title_bonus = 0.1 if source.get("title") else 0.0
    return max(0.05, min(1.0, 0.2 + (0.7 * length_score) + title_bonus))


class SourceRanker:

    def rank_sources(self, query, sources, limit=5):
        ranked = []
        for source in sources or []:
            source = _normalize_source(source)
            url = source.get("url", "")
            reliability = _domain_reliability(url)
            relevance = _relevance_score(query, source)
            freshness = _freshness_score(source)
            completeness = _completeness_score(source)
            score = (
                0.35 * reliability
                + 0.35 * relevance
                + 0.15 * freshness
                + 0.15 * completeness
            )
            ranked.append(
                {
                    **source,
                    "reliability": round(reliability, 3),
                    "relevance": round(relevance, 3),
                    "freshness": round(freshness, 3),
                    "completeness": round(completeness, 3),
                    "score": round(score, 3),
                }
            )

        ranked.sort(key=lambda item: (item.get("score", 0.0), item.get("relevance", 0.0)), reverse=True)
        return ranked[:limit]
