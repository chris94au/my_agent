import json
import logging
import math
import sqlite3
from datetime import datetime, timezone

from embedding import Embedding
from normalizer import Normalizer
from similarity import cosine_similarity


logger = logging.getLogger(__name__)


class Memory:

    MIN_IMPORTANCE = 1
    MAX_IMPORTANCE = 10
    DEFAULT_IMPORTANCE = 5
    DEFAULT_CONFIDENCE = 0.75
    RECENCY_HALF_LIFE_DAYS = 45.0
    ARCHIVE_MIN_AGE_DAYS = 30
    ARCHIVE_COMPOSITE_THRESHOLD = 0.35
    FACT_DUPLICATE_THRESHOLD = 0.86
    SUMMARY_DUPLICATE_THRESHOLD = 0.84


    def __init__(self, db_path="memory.db"):

        self.connection = sqlite3.connect(
            db_path
        )
        self.connection.row_factory = sqlite3.Row

        self.embedder = Embedding()
        self.normalizer = Normalizer()

        self._ensure_schema()


    def _ensure_schema(self):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 5,
                confidence REAL NOT NULL DEFAULT 0.75,
                status TEXT NOT NULL DEFAULT 'active',
                occurrence_count INTEGER NOT NULL DEFAULT 1,
                use_count INTEGER NOT NULL DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                archived_at DATETIME,
                archive_reason TEXT,
                embedding TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                summary TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 5,
                confidence REAL NOT NULL DEFAULT 0.65,
                status TEXT NOT NULL DEFAULT 'active',
                occurrence_count INTEGER NOT NULL DEFAULT 1,
                use_count INTEGER NOT NULL DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                archived_at DATETIME,
                archive_reason TEXT,
                embedding TEXT
            )
            """
        )

        self._migrate_table(
            "facts",
            {
                "confidence": "REAL",
                "status": "TEXT",
                "occurrence_count": "INTEGER",
                "use_count": "INTEGER",
                "last_seen_at": "DATETIME",
                "last_used_at": "DATETIME",
                "archived_at": "DATETIME",
                "archive_reason": "TEXT"
            }
        )

        self._migrate_table(
            "summaries",
            {
                "confidence": "REAL",
                "status": "TEXT",
                "occurrence_count": "INTEGER",
                "use_count": "INTEGER",
                "last_seen_at": "DATETIME",
                "last_used_at": "DATETIME",
                "archived_at": "DATETIME",
                "archive_reason": "TEXT"
            }
        )

        self._backfill_defaults()
        self.connection.commit()


    def _migrate_table(self, table_name, columns):

        cursor = self.connection.cursor()
        cursor.execute(
            f"PRAGMA table_info({table_name})"
        )
        existing = {
            row[1]
            for row in cursor.fetchall()
        }

        for column_name, column_type in columns.items():
            if column_name not in existing:
                logger.info(
                    "Migrating %s: adding column %s",
                    table_name,
                    column_name
                )
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )


    def _backfill_defaults(self):
        cursor = self.connection.cursor()

        cursor.execute(
            """
            UPDATE facts
            SET confidence = COALESCE(confidence, 0.75),
                status = COALESCE(status, 'active'),
                occurrence_count = COALESCE(occurrence_count, 1),
                use_count = COALESCE(use_count, 0),
                last_seen_at = COALESCE(last_seen_at, timestamp, CURRENT_TIMESTAMP),
                last_used_at = COALESCE(last_used_at, timestamp, CURRENT_TIMESTAMP)
            """
        )

        cursor.execute(
            """
            UPDATE summaries
            SET confidence = COALESCE(confidence, 0.65),
                status = COALESCE(status, 'active'),
                occurrence_count = COALESCE(occurrence_count, 1),
                use_count = COALESCE(use_count, 0),
                last_seen_at = COALESCE(last_seen_at, timestamp, CURRENT_TIMESTAMP),
                last_used_at = COALESCE(last_used_at, timestamp, CURRENT_TIMESTAMP)
            """
        )


    def _clean_text(self, value):
        return " ".join(
            str(value).strip().split()
        )


    def _clamp_importance(self, importance):
        try:
            value = int(round(float(importance)))
        except Exception:
            value = self.DEFAULT_IMPORTANCE

        return max(
            self.MIN_IMPORTANCE,
            min(self.MAX_IMPORTANCE, value)
        )


    def _clamp_confidence(self, confidence):
        try:
            value = float(confidence)
        except Exception:
            value = self.DEFAULT_CONFIDENCE

        return max(
            0.0,
            min(1.0, value)
        )


    def _parse_timestamp(self, value):
        if not value:
            return None

        try:
            return datetime.fromisoformat(
                str(value).replace(
                    " ",
                    "T"
                )
            )
        except ValueError:
            return None


    def _now(self):
        return datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )


    def _days_since(self, value):
        parsed = self._parse_timestamp(value)
        if not parsed:
            return 0.0

        delta = self._now() - parsed
        return max(delta.total_seconds() / 86400.0, 0.0)


    def _recency_score(self, value):
        age_days = self._days_since(value)
        return math.exp(
            -age_days / self.RECENCY_HALF_LIFE_DAYS
        )


    def _build_fact_embedding_text(self, category, key, value):
        return (
            f"{category}: "
            f"{key}: "
            f"{value}"
        )


    def _build_summary_embedding_text(self, topic, summary):
        return (
            f"{topic}: "
            f"{summary}"
        )


    def _normalize_fact_inputs(self, category, key, value):
        fact = {
            "category": category,
            "key": key,
            "value": value
        }
        return self.normalizer.normalize_fact(
            fact
        )


    def _normalize_summary_inputs(self, topic, summary):
        return self.normalizer.normalize_summary(
            {
                "topic": topic,
                "summary": summary
            }
        )


    def _row_to_dict(self, row):
        if row is None:
            return None

        return dict(row)


    def _fetch_rows(self, table_name, include_archived=False):
        cursor = self.connection.cursor()

        if include_archived:
            cursor.execute(
                f"SELECT * FROM {table_name}"
            )
        else:
            cursor.execute(
                f"SELECT * FROM {table_name} WHERE status = 'active'"
            )

        return [dict(row) for row in cursor.fetchall()]


    def _fetch_exact_fact(self, category, key, include_archived=True):
        cursor = self.connection.cursor()

        if include_archived:
            cursor.execute(
                """
                SELECT *
                FROM facts
                WHERE LOWER(TRIM(category)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(key)) = LOWER(TRIM(?))
                ORDER BY CASE WHEN status = 'active' THEN 0 ELSE 1 END,
                         last_seen_at DESC,
                         id DESC
                LIMIT 1
                """,
                (category, key)
            )
        else:
            cursor.execute(
                """
                SELECT *
                FROM facts
                WHERE LOWER(TRIM(category)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(key)) = LOWER(TRIM(?))
                  AND status = 'active'
                ORDER BY last_seen_at DESC,
                         id DESC
                LIMIT 1
                """,
                (category, key)
            )

        return self._row_to_dict(
            cursor.fetchone()
        )


    def _fetch_exact_summary(self, topic, include_archived=True):
        cursor = self.connection.cursor()

        if include_archived:
            cursor.execute(
                """
                SELECT *
                FROM summaries
                WHERE LOWER(TRIM(topic)) = LOWER(TRIM(?))
                ORDER BY CASE WHEN status = 'active' THEN 0 ELSE 1 END,
                         last_seen_at DESC,
                         id DESC
                LIMIT 1
                """,
                (topic,)
            )
        else:
            cursor.execute(
                """
                SELECT *
                FROM summaries
                WHERE LOWER(TRIM(topic)) = LOWER(TRIM(?))
                  AND status = 'active'
                ORDER BY last_seen_at DESC,
                         id DESC
                LIMIT 1
                """,
                (topic,)
            )

        return self._row_to_dict(
            cursor.fetchone()
        )


    def _find_best_fact_match(self, category, key, value, threshold=None, include_archived=True):
        if threshold is None:
            threshold = self.FACT_DUPLICATE_THRESHOLD

        query_text = self._build_fact_embedding_text(
            category,
            key,
            value
        )
        query_embedding = self.embedder.create(
            query_text
        )

        best = None
        for candidate in self._fetch_rows(
            "facts",
            include_archived=include_archived
        ):
            if not candidate.get("embedding"):
                continue

            try:
                candidate_embedding = json.loads(
                    candidate["embedding"]
                )
            except (TypeError, json.JSONDecodeError):
                continue

            score = cosine_similarity(
                query_embedding,
                candidate_embedding
            )

            if score < threshold:
                continue

            if best is None or score > best["similarity"]:
                best = {
                    **candidate,
                    "similarity": score,
                    "match_type": "semantic"
                }

        return best


    def _find_best_summary_match(self, topic, summary, threshold=None, include_archived=True):
        if threshold is None:
            threshold = self.SUMMARY_DUPLICATE_THRESHOLD

        query_text = self._build_summary_embedding_text(
            topic,
            summary
        )
        query_embedding = self.embedder.create(
            query_text
        )

        best = None
        for candidate in self._fetch_rows(
            "summaries",
            include_archived=include_archived
        ):
            if not candidate.get("embedding"):
                continue

            try:
                candidate_embedding = json.loads(
                    candidate["embedding"]
                )
            except (TypeError, json.JSONDecodeError):
                continue

            score = cosine_similarity(
                query_embedding,
                candidate_embedding
            )

            if score < threshold:
                continue

            if best is None or score > best["similarity"]:
                best = {
                    **candidate,
                    "similarity": score,
                    "match_type": "semantic"
                }

        return best


    def _evolve_importance(self, existing_importance, incoming_importance, occurrence_count):
        base = max(
            self._clamp_importance(existing_importance),
            self._clamp_importance(incoming_importance)
        )

        if occurrence_count >= 2:
            base = max(
                base,
                self._clamp_importance(existing_importance) + 1
            )

        return self._clamp_importance(
            base
        )


    def _evolve_confidence(self, existing_confidence, incoming_confidence, occurrence_count):
        confidence = max(
            self._clamp_confidence(existing_confidence),
            self._clamp_confidence(incoming_confidence)
        )

        confidence += min(
            0.05 * max(occurrence_count - 1, 0),
            0.20
        )

        return self._clamp_confidence(
            confidence
        )


    def _update_fact_row(self, fact, importance, confidence, new_value=None):
        occurrence_count = int(fact.get("occurrence_count", 1) or 1) + 1
        updated_importance = self._evolve_importance(
            fact.get("importance", self.DEFAULT_IMPORTANCE),
            importance,
            occurrence_count
        )
        updated_confidence = self._evolve_confidence(
            fact.get("confidence", self.DEFAULT_CONFIDENCE),
            confidence,
            occurrence_count
        )
        value = new_value if new_value is not None else fact["value"]

        embedding_text = self._build_fact_embedding_text(
            fact["category"],
            fact["key"],
            value
        )
        embedding = self.embedder.create(
            embedding_text
        )

        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE facts
            SET value = ?,
                importance = ?,
                confidence = ?,
                status = 'active',
                occurrence_count = ?,
                last_seen_at = CURRENT_TIMESTAMP,
                last_used_at = CURRENT_TIMESTAMP,
                archived_at = NULL,
                archive_reason = NULL,
                embedding = ?
            WHERE id = ?
            """,
            (
                value,
                updated_importance,
                updated_confidence,
                occurrence_count,
                json.dumps(embedding),
                fact["id"]
            )
        )

        self.connection.commit()

        return {
            **fact,
            "value": value,
            "importance": updated_importance,
            "confidence": updated_confidence,
            "occurrence_count": occurrence_count,
            "status": "active",
            "match_type": fact.get("match_type", "slot")
        }


    def _update_summary_row(self, summary_row, importance, confidence, new_summary=None):
        occurrence_count = int(summary_row.get("occurrence_count", 1) or 1) + 1
        updated_importance = self._evolve_importance(
            summary_row.get("importance", self.DEFAULT_IMPORTANCE),
            importance,
            occurrence_count
        )
        updated_confidence = self._evolve_confidence(
            summary_row.get("confidence", self.DEFAULT_CONFIDENCE),
            confidence,
            occurrence_count
        )
        summary_text = new_summary if new_summary is not None else summary_row["summary"]

        embedding_text = self._build_summary_embedding_text(
            summary_row["topic"],
            summary_text
        )
        embedding = self.embedder.create(
            embedding_text
        )

        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE summaries
            SET summary = ?,
                importance = ?,
                confidence = ?,
                status = 'active',
                occurrence_count = ?,
                last_seen_at = CURRENT_TIMESTAMP,
                last_used_at = CURRENT_TIMESTAMP,
                archived_at = NULL,
                archive_reason = NULL,
                embedding = ?
            WHERE id = ?
            """,
            (
                summary_text,
                updated_importance,
                updated_confidence,
                occurrence_count,
                json.dumps(embedding),
                summary_row["id"]
            )
        )

        self.connection.commit()

        return {
            **summary_row,
            "summary": summary_text,
            "importance": updated_importance,
            "confidence": updated_confidence,
            "occurrence_count": occurrence_count,
            "status": "active",
            "match_type": summary_row.get("match_type", "slot")
        }


    def save_fact(self, category, key, value, importance=5, confidence=None):
        normalized = self._normalize_fact_inputs(
            category,
            key,
            value
        )
        category = normalized["category"]
        key = normalized["key"]
        value = normalized["value"]
        importance = self._clamp_importance(
            importance
        )
        confidence = self._clamp_confidence(
            confidence if confidence is not None else self.DEFAULT_CONFIDENCE
        )

        existing = self._fetch_exact_fact(
            category,
            key,
            include_archived=True
        )

        if existing:
            value_changed = self._clean_text(existing["value"]) != self._clean_text(value)
            new_value = value if value_changed else None
            existing["match_type"] = "slot"
            logger.info(
                "Consolidating fact slot %s / %s",
                category,
                key
            )
            return self._update_fact_row(
                existing,
                importance,
                confidence,
                new_value=new_value
            )

        existing = self._find_best_fact_match(
            category,
            key,
            value,
            include_archived=True
        )

        if existing:
            logger.info(
                "Consolidating semantic fact match for %s / %s",
                category,
                key
            )
            return self._update_fact_row(
                existing,
                importance,
                confidence,
                new_value=None
            )

        embedding_text = self._build_fact_embedding_text(
            category,
            key,
            value
        )
        embedding = self.embedder.create(
            embedding_text
        )

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO facts
            (category, key, value, importance, confidence, status, occurrence_count, embedding)
            VALUES (?, ?, ?, ?, ?, 'active', 1, ?)
            """,
            (
                category,
                key,
                value,
                importance,
                confidence,
                json.dumps(embedding)
            )
        )
        self.connection.commit()

        logger.info(
            "Inserted new fact memory %s / %s",
            category,
            key
        )

        return {
            "status": "inserted",
            "category": category,
            "key": key,
            "value": value,
            "importance": importance,
            "confidence": confidence
        }


    def save_summary(self, topic, summary, importance=5, confidence=None):
        normalized = self._normalize_summary_inputs(
            topic,
            summary
        )
        topic = normalized["topic"]
        summary = normalized["summary"]
        importance = self._clamp_importance(
            importance
        )
        confidence = self._clamp_confidence(
            confidence if confidence is not None else 0.65
        )

        if not topic or not summary:
            return {"status": "skipped"}

        existing = self._fetch_exact_summary(
            topic,
            include_archived=True
        )

        if existing:
            new_summary = summary if len(summary) >= len(existing["summary"]) else None
            existing["match_type"] = "slot"
            logger.info(
                "Consolidating summary slot %s",
                topic
            )
            return self._update_summary_row(
                existing,
                importance,
                confidence,
                new_summary=new_summary
            )

        existing = self._find_best_summary_match(
            topic,
            summary,
            include_archived=True
        )

        if existing:
            logger.info(
                "Consolidating semantic summary match for %s",
                topic
            )
            return self._update_summary_row(
                existing,
                importance,
                confidence,
                new_summary=None
            )

        embedding_text = self._build_summary_embedding_text(
            topic,
            summary
        )
        embedding = self.embedder.create(
            embedding_text
        )

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO summaries
            (topic, summary, importance, confidence, status, occurrence_count, embedding)
            VALUES (?, ?, ?, ?, 'active', 1, ?)
            """,
            (
                topic,
                summary,
                importance,
                confidence,
                json.dumps(embedding)
            )
        )
        self.connection.commit()

        logger.info(
            "Inserted new summary memory %s",
            topic
        )

        return {
            "status": "inserted",
            "topic": topic,
            "summary": summary,
            "importance": importance,
            "confidence": confidence
        }


    def _decay_score(self, item):
        importance = self._clamp_importance(
            item.get("importance", self.DEFAULT_IMPORTANCE)
        )
        confidence = self._clamp_confidence(
            item.get("confidence", self.DEFAULT_CONFIDENCE)
        )
        recency = self._recency_score(
            item.get("last_used_at") or item.get("last_seen_at") or item.get("timestamp")
        )
        use_count = int(item.get("use_count", 0) or 0)
        usage_bonus = min(use_count / 20.0, 0.1)

        importance_score = (importance - self.MIN_IMPORTANCE) / (
            self.MAX_IMPORTANCE - self.MIN_IMPORTANCE
        )

        return (
            0.4 * importance_score
            + 0.3 * confidence
            + 0.2 * recency
            + usage_bonus
        )


    def archive_low_value_memories(self):
        archived = []
        cursor = self.connection.cursor()

        for table_name, age_limit in (("facts", self.ARCHIVE_MIN_AGE_DAYS), ("summaries", self.ARCHIVE_MIN_AGE_DAYS * 2)):
            for item in self._fetch_rows(table_name, include_archived=False):
                age_days = self._days_since(
                    item.get("last_used_at") or item.get("last_seen_at") or item.get("timestamp")
                )

                if age_days < age_limit:
                    continue

                if int(item.get("occurrence_count", 1) or 1) > 2:
                    continue

                if self._clamp_importance(item.get("importance", self.DEFAULT_IMPORTANCE)) >= 6:
                    continue

                if self._clamp_confidence(item.get("confidence", self.DEFAULT_CONFIDENCE)) >= 0.75:
                    continue

                score = self._decay_score(item)
                if score >= self.ARCHIVE_COMPOSITE_THRESHOLD:
                    continue

                cursor.execute(
                    f"""
                    UPDATE {table_name}
                    SET status = 'archived',
                        archived_at = CURRENT_TIMESTAMP,
                        archive_reason = ?
                    WHERE id = ?
                    """,
                    (
                        "low_relevance_decay",
                        item["id"]
                    )
                )
                archived.append(
                    {
                        "table": table_name,
                        "id": item["id"],
                        "score": score
                    }
                )

        if archived:
            self.connection.commit()
            logger.info(
                "Archived %d low-value memories",
                len(archived)
            )

        return archived


    def _final_score(self, item, similarity):
        importance = self._clamp_importance(
            item.get("importance", self.DEFAULT_IMPORTANCE)
        )
        confidence = self._clamp_confidence(
            item.get("confidence", self.DEFAULT_CONFIDENCE)
        )
        recency = self._recency_score(
            item.get("last_used_at") or item.get("last_seen_at") or item.get("timestamp")
        )
        importance_score = (importance - self.MIN_IMPORTANCE) / (
            self.MAX_IMPORTANCE - self.MIN_IMPORTANCE
        )
        usage_bonus = min(
            int(item.get("occurrence_count", 1) or 1) / 15.0,
            0.15
        )
        status_penalty = 0.75 if item.get("status") == "archived" else 1.0

        score = (
            0.38 * similarity
            + 0.24 * importance_score
            + 0.20 * confidence
            + 0.15 * recency
            + usage_bonus
        )

        return score * status_penalty


    def _update_access(self, table_name, ids):
        if not ids:
            return

        cursor = self.connection.cursor()
        cursor.executemany(
            f"""
            UPDATE {table_name}
            SET last_used_at = CURRENT_TIMESTAMP,
                use_count = COALESCE(use_count, 0) + 1
            WHERE id = ?
            """,
            [(item_id,) for item_id in ids]
        )
        self.connection.commit()


    def get_relevant_memories(self, query, limit=5, include_archived=False):
        if not query:
            return []

        self.archive_low_value_memories()

        query_embedding = self.embedder.create(
            query
        )

        candidates = []

        for item in self._fetch_rows(
            "facts",
            include_archived=include_archived
        ):
            if not item.get("embedding"):
                continue

            try:
                item_embedding = json.loads(
                    item["embedding"]
                )
            except (TypeError, json.JSONDecodeError):
                continue

            similarity = cosine_similarity(
                query_embedding,
                item_embedding
            )
            candidates.append(
                {
                    **item,
                    "item_type": "fact",
                    "similarity": similarity,
                    "final_score": self._final_score(item, similarity)
                }
            )

        for item in self._fetch_rows(
            "summaries",
            include_archived=include_archived
        ):
            if not item.get("embedding"):
                continue

            try:
                item_embedding = json.loads(
                    item["embedding"]
                )
            except (TypeError, json.JSONDecodeError):
                continue

            similarity = cosine_similarity(
                query_embedding,
                item_embedding
            )
            candidates.append(
                {
                    **item,
                    "item_type": "summary",
                    "similarity": similarity,
                    "final_score": self._final_score(item, similarity)
                }
            )

        candidates.sort(
            key=lambda item: item["final_score"],
            reverse=True
        )

        selected = candidates[:limit]
        fact_ids = [
            item["id"]
            for item in selected
            if item["item_type"] == "fact"
        ]
        summary_ids = [
            item["id"]
            for item in selected
            if item["item_type"] == "summary"
        ]

        self._update_access(
            "facts",
            fact_ids
        )
        self._update_access(
            "summaries",
            summary_ids
        )

        return selected


    def get_semantic_context(self, query, limit=5):
        memories = self.get_relevant_memories(
            query,
            limit=limit
        )

        if not memories:
            return ""

        context = (
            "Bekannte Informationen über den Benutzer:\n"
        )

        for memory in memories:
            if memory["item_type"] == "summary":
                context += (
                    f"- [Zusammenfassung] {memory['topic']}: {memory['summary']} "
                    f"(Score: {memory['final_score']:.2f}, "
                    f"Importance: {memory['importance']}, "
                    f"Confidence: {memory['confidence']:.2f})\n"
                )
            else:
                context += (
                    f"- [{memory['category']}] {memory['key']}: {memory['value']} "
                    f"(Score: {memory['final_score']:.2f}, "
                    f"Importance: {memory['importance']}, "
                    f"Confidence: {memory['confidence']:.2f})\n"
                )

        return context


    def get_context(self, query=None):
        if query:
            return self.get_semantic_context(
                query
            )

        facts = self.get_all_facts()
        summaries = self.get_all_summaries()

        if not facts and not summaries:
            return ""

        context = (
            "Bekannte Informationen über den Benutzer:\n"
        )

        for fact in facts:
            context += (
                f"- [{fact['category']}] {fact['key']}: {fact['value']} "
                f"(Importance: {fact['importance']}, Confidence: {fact['confidence']:.2f})\n"
            )

        for summary in summaries:
            context += (
                f"- [Zusammenfassung] {summary['topic']}: {summary['summary']} "
                f"(Importance: {summary['importance']}, Confidence: {summary['confidence']:.2f})\n"
            )

        return context


    def get_all_facts(self, include_archived=False):
        return self._fetch_rows(
            "facts",
            include_archived=include_archived
        )


    def get_all_summaries(self, include_archived=False):
        return self._fetch_rows(
            "summaries",
            include_archived=include_archived
        )


    def search(self, query):
        if not query:
            return []

        query = self._clean_text(query).casefold()
        words = query.split()
        results = []

        for item in self._fetch_rows("facts", include_archived=False):
            haystack = " ".join(
                [
                    str(item.get("category", "")),
                    str(item.get("key", "")),
                    str(item.get("value", ""))
                ]
            ).casefold()
            if any(word in haystack for word in words):
                results.append(item)

        for item in self._fetch_rows("summaries", include_archived=False):
            haystack = " ".join(
                [
                    str(item.get("topic", "")),
                    str(item.get("summary", ""))
                ]
            ).casefold()
            if any(word in haystack for word in words):
                results.append(item)

        return results


    def close(self):
        self.connection.close()
