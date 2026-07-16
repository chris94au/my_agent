from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CitationRecord:
    claim: str
    source: str
    timestamp: str
    confidence: float
    metadata: dict = field(default_factory=dict)


class CitationTracker:

    def __init__(self):
        self._records: list[CitationRecord] = []


    def record(self, claim, source, confidence=0.5, timestamp=None, metadata=None):
        record = CitationRecord(
            claim=str(claim),
            source=str(source),
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            confidence=max(0.0, min(1.0, float(confidence))),
            metadata=dict(metadata or {}),
        )
        self._records.append(record)
        return record


    def extend(self, records):
        for record in records or []:
            if isinstance(record, CitationRecord):
                self._records.append(record)
            elif isinstance(record, dict):
                self.record(
                    claim=record.get("claim", ""),
                    source=record.get("source", ""),
                    confidence=record.get("confidence", 0.5),
                    timestamp=record.get("timestamp"),
                    metadata=record.get("metadata", {}),
                )
        return self._records


    def all(self):
        return [record.__dict__.copy() for record in self._records]


    def by_source(self, source):
        return [record.__dict__.copy() for record in self._records if record.source == source]


    def as_context(self):
        if not self._records:
            return ""

        lines = ["Quellenverfolgung:"]
        for record in self._records:
            lines.append(
                f"- {record.claim} <- {record.source} (confidence={record.confidence:.2f}, timestamp={record.timestamp})"
            )
        return "\n".join(lines)
