import json
import sqlite3

from embedding import Embedding
from similarity import cosine_similarity
from normalizer import Normalizer


class Memory:

    SEMANTIC_DUPLICATE_THRESHOLD = 0.86


    def __init__(self, db_path="memory.db"):

        self.connection = sqlite3.connect(
            db_path
        )

        self.embedder = Embedding()
        self.normalizer = Normalizer()

        self.create_table()



    def create_table(self):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                category TEXT,

                key TEXT,

                value TEXT,

                importance INTEGER,

                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

                embedding TEXT
            )
            """
        )

        self.connection.commit()



    def _normalize_fact_inputs(
        self,
        category,
        key,
        value
    ):

        fact = {
            "category": category,
            "key": key,
            "value": value
        }

        return self.normalizer.normalize(
            fact
        )


    def _normalize_text(self, text):

        return " ".join(
            str(text).strip().split()
        ).casefold()


    def _build_embedding_text(
        self,
        category,
        key,
        value
    ):

        return (
            f"{category}: "
            f"{key}: "
            f"{value}"
        )


    def _row_to_fact(self, row):

        if not row:
            return None

        fact_id, category, key, value, importance = row

        return {
            "id": fact_id,
            "category": category,
            "key": key,
            "value": value,
            "importance": importance
        }


    def _fetch_fact_by_slot(
        self,
        category,
        key
    ):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                category,
                key,
                value,
                importance
            FROM facts
            WHERE LOWER(TRIM(category)) = LOWER(TRIM(?))
              AND LOWER(TRIM(key)) = LOWER(TRIM(?))
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
            """,
            (
                category,
                key
            )
        )

        return self._row_to_fact(
            cursor.fetchone()
        )


    def _fetch_facts_with_embeddings(self):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                category,
                key,
                value,
                importance,
                embedding
            FROM facts
            WHERE embedding IS NOT NULL
            """
        )

        facts = []

        for row in cursor.fetchall():

            fact_id, category, key, value, importance, embedding_json = row

            try:
                embedding = json.loads(
                    embedding_json
                )
            except (TypeError, json.JSONDecodeError):
                continue

            facts.append(
                {
                    "id": fact_id,
                    "category": category,
                    "key": key,
                    "value": value,
                    "importance": importance,
                    "embedding": embedding
                }
            )

        return facts


    def _remove_duplicate_slot_rows(
        self,
        category,
        key,
        keep_id
    ):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            DELETE FROM facts
            WHERE LOWER(TRIM(category)) = LOWER(TRIM(?))
              AND LOWER(TRIM(key)) = LOWER(TRIM(?))
              AND id != ?
            """,
            (
                category,
                key,
                keep_id
            )
        )

        self.connection.commit()


    def _find_best_semantic_duplicate(
        self,
        category,
        key,
        value,
        threshold=None
    ):

        if threshold is None:
            threshold = self.SEMANTIC_DUPLICATE_THRESHOLD

        query_text = self._build_embedding_text(
            category,
            key,
            value
        )

        query_embedding = self.embedder.create(
            query_text
        )

        best_match = None

        for fact in self._fetch_facts_with_embeddings():

            score = cosine_similarity(
                query_embedding,
                fact["embedding"]
            )

            if score < threshold:
                continue

            if best_match is None or score > best_match["score"]:

                best_match = {
                    "id": fact["id"],
                    "category": fact["category"],
                    "key": fact["key"],
                    "value": fact["value"],
                    "importance": fact["importance"],
                    "score": score,
                    "match_type": "semantic"
                }

        return best_match


    def save_fact(
        self,
        category,
        key,
        value,
        importance=5
    ):

        normalized_fact = self._normalize_fact_inputs(
            category,
            key,
            value
        )

        category = normalized_fact["category"]
        key = normalized_fact["key"]
        value = normalized_fact["value"]

        existing = self.find_similar_fact(
            category,
            key,
            value
        )

        if existing:

            print(
                "MEMORY UPDATE:",
                existing
            )

            if existing.get("match_type") == "slot":

                value_changed = self._normalize_text(
                    existing["value"]
                ) != self._normalize_text(
                    value
                )

                self.update_fact(
                    existing,
                    importance,
                    new_value=value if value_changed else None
                )

            else:

                self.update_fact(
                    existing,
                    importance,
                    new_value=None
                )

            return "updated"



        text = self._build_embedding_text(
            category,
            key,
            value
        )


        embedding = self.embedder.create(
            text
        )


        embedding_json = json.dumps(
            embedding
        )


        cursor = self.connection.cursor()


        cursor.execute(
            """
            INSERT INTO facts
            (
                category,
                key,
                value,
                importance,
                embedding
            )

            VALUES (?, ?, ?, ?, ?)

            """,
            (
                category,
                key,
                value,
                importance,
                embedding_json
            )
        )


        self.connection.commit()


        print(
            "INSERTING NEW MEMORY"
        )
        return "inserted"


    def find_similar_fact(
        self,
        category,
        key,
        value,
        threshold=0.80
    ):

        query = self._normalize_fact_inputs(
            category,
            key,
            value
        )

        exact = self._fetch_fact_by_slot(
            query["category"],
            query["key"]
        )

        if exact:

            exact["match_type"] = "slot"
            exact["score"] = 1.0
            return exact

        return self._find_best_semantic_duplicate(
            query["category"],
            query["key"],
            query["value"],
            threshold=threshold
        )


    def update_fact(
        self,
        old_fact,
        new_importance,
        new_value=None
    ):

        cursor = self.connection.cursor()


        importance = max(
            old_fact["importance"],
            new_importance
        )


        if new_value is None:

            if "id" in old_fact:

                cursor.execute(
                    """
                    UPDATE facts

                    SET importance = ?

                    WHERE id = ?

                    """,
                    (
                        importance,
                        old_fact["id"]
                    )
                )

            else:

                cursor.execute(
                    """
                    UPDATE facts

                    SET importance = ?

                    WHERE
                    category = ?

                    AND

                    key = ?

                    AND

                    value = ?

                    """,
                    (
                        importance,

                        old_fact["category"],

                        old_fact["key"],

                        old_fact["value"]
                    )
                )

        else:

            embedding_text = self._build_embedding_text(
                old_fact["category"],
                old_fact["key"],
                new_value
            )

            embedding = self.embedder.create(
                embedding_text
            )

            if "id" in old_fact:

                cursor.execute(
                    """
                    UPDATE facts

                    SET importance = ?,
                        value = ?,
                        embedding = ?

                    WHERE id = ?

                    """,
                    (
                        importance,
                        new_value,
                        json.dumps(embedding),
                        old_fact["id"]
                    )
                )

            else:

                cursor.execute(
                    """
                    UPDATE facts

                    SET importance = ?,
                        value = ?,
                        embedding = ?

                    WHERE
                    category = ?

                    AND

                    key = ?

                    AND

                    value = ?

                    """,
                    (
                        importance,
                        new_value,
                        json.dumps(embedding),

                        old_fact["category"],

                        old_fact["key"],

                        old_fact["value"]
                    )
                )


        self.connection.commit()

        if old_fact.get("match_type") == "slot":
            self._remove_duplicate_slot_rows(
                old_fact["category"],
                old_fact["key"],
                old_fact.get("id")
            )


        print(
            "MEMORY UPDATED"
        )



    def semantic_search(
        self,
        query,
        limit=5
    ):

        query_embedding = self.embedder.create(
            query
        )


        cursor = self.connection.cursor()


        cursor.execute(
            """
            SELECT

                category,

                key,

                value,

                importance,

                embedding

            FROM facts

            WHERE embedding IS NOT NULL

            """
        )


        rows = cursor.fetchall()


        results = []


        for row in rows:


            category, key, value, importance, embedding_json = row


            embedding = json.loads(
                embedding_json
            )


            score = cosine_similarity(
                query_embedding,
                embedding
            )


            results.append(
                (
                    category,
                    key,
                    value,
                    importance,
                    score
                )
            )


        results.sort(
            key=lambda x: x[4],
            reverse=True
        )


        return results[:limit]



    def search(
        self,
        query
    ):

        cursor = self.connection.cursor()


        words = query.lower().split()


        results = []


        for word in words:

            cursor.execute(
                """
                SELECT

                    category,

                    key,

                    value,

                    importance,

                    timestamp

                FROM facts

                WHERE

                LOWER(category) LIKE ?

                OR LOWER(key) LIKE ?

                OR LOWER(value) LIKE ?

                """,
                (
                    f"%{word}%",

                    f"%{word}%",

                    f"%{word}%"
                )
            )


            results.extend(
                cursor.fetchall()
            )


        return list(
            set(results)
        )

    def get_semantic_context(
        self,
        query
    ):

        facts = self.semantic_search(
            query,
            limit=5
        )


        # nur relevante Treffer verwenden
        facts = [
            fact
            for fact in facts
            if fact[4] >= 0.50
        ]


        if not facts:
            return ""


        context = (
            "Bekannte Informationen "
            "über den Benutzer:\n"
        )


        for fact in facts:

            category, key, value, importance, score = fact


            context += (
                f"- [{category}] "
                f"{key}: {value} "
                f"(Relevanz: {score:.2f})\n"
            )


        return context


    def get_context(
        self,
        query=None
    ):


        if query:

            facts = self.semantic_search(
                query
            )

            facts = [
                f
                for f in facts
                if f[4] >= 0.50
            ]

        else:

            facts = self.get_all_facts()



        if not facts:

            return ""



        context = (
            "Bekannte Informationen "
            "über den Benutzer:\n"
        )



        for fact in facts:


            category, key, value, importance, score = fact



            context += (
                f"- Der Benutzer "
                f"interessiert sich für "
                f"{value}.\n"
            )


        return context



    def get_all_facts(self):

        cursor = self.connection.cursor()


        cursor.execute(
            """
            SELECT

                category,

                key,

                value,

                importance,

                timestamp

            FROM facts

            """
        )


        return cursor.fetchall()



    def close(self):

        self.connection.close()
