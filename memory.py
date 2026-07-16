import sqlite3
import json

from embedding import Embedding
from similarity import cosine_similarity


class Memory:

    def __init__(self, db_path="memory.db"):

        self.connection = sqlite3.connect(
            db_path
        )

        self.embedder = Embedding()

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



    def save_fact(
        self,
        category,
        key,
        value,
        importance=5
    ):

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

            self.update_fact(
                existing,
                importance
            )

            return "updated"



        text = (
            f"{category}: "
            f"{value}"
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

        query = (
            f"{category}: "
            f"{value}"
        )


        results = self.semantic_search(
            query,
            limit=5
        )


        for result in results:


            old_category, old_key, old_value, old_importance, score = result


            print(
                "MEMORY SIMILARITY CHECK:",
                old_value,
                score
            )


            if score >= threshold:

                return {

                    "category": old_category,

                    "key": old_key,

                    "value": old_value,

                    "importance": old_importance,

                    "score": score
                }


        return None



    def update_fact(
        self,
        old_fact,
        new_importance
    ):

        cursor = self.connection.cursor()


        importance = max(
            old_fact["importance"],
            new_importance
        )


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


        self.connection.commit()


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