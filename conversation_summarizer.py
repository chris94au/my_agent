import json
import logging
import re

import ollama


logger = logging.getLogger(__name__)


class ConversationSummarizer:


    def __init__(self, model="qwen2.5:7b"):

        self.model = model


    def _conversation_excerpt(self, conversation, limit=5000):
        if not conversation:
            return ""

        text = str(conversation).strip()
        if len(text) <= limit:
            return text

        return text[-limit:]


    def _fallback_summary(self, conversation, memories):
        excerpt = self._conversation_excerpt(
            conversation,
            limit=900
        )

        memory_bits = []
        for memory in memories or []:
            if isinstance(memory, dict):
                value = memory.get("value")
                key = memory.get("key")
                if value and key:
                    memory_bits.append(f"{key}: {value}")

        summary_parts = []
        if memory_bits:
            summary_parts.append(
                "Langfristig relevante Fakten: " + ", ".join(memory_bits[:4])
            )

        if excerpt:
            summary_parts.append(
                "Kurzer Gesprächskontext: " + excerpt[:400]
            )

        summary = " ".join(summary_parts).strip()
        if not summary:
            return None

        return {
            "topic": "Gesprächszusammenfassung",
            "summary": summary,
            "importance": 5,
            "confidence": 0.55
        }


    def summarize(self, conversation, memories=None):

        excerpt = self._conversation_excerpt(
            conversation
        )

        prompt = f"""
Du bist ein Conversation-Summarizer für einen langfristigen AI-Agenten.

Erstelle eine knappe, aber nützliche Zusammenfassung der Unterhaltung.
Speichere nur langfristig wertvolle Kontexte: laufende Projekte,
bevorzugte Arbeitsweisen, stabile Interessen, wichtige Entscheidungen.

Die Zusammenfassung darf Fakten nicht ersetzen. Sie ergänzt die Faktenebene.

Eingaben:
Kontext:
{excerpt}

Extrahierte Fakten:
{json.dumps(memories or [], ensure_ascii=False)}

Antworte ausschließlich mit JSON.

Wenn sinnvoll:
{{
    "topic": "kurzes_thema",
    "summary": "mehrsätzige, langfristig nützliche Zusammenfassung",
    "importance": 1-10,
    "confidence": 0.0-1.0
}}

Wenn keine langfristig nützliche Zusammenfassung möglich ist:
{{
    "topic": "",
    "summary": "",
    "importance": 0,
    "confidence": 0.0
}}
"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
        except Exception as exc:
            logger.warning(
                "Conversation summary fallback due to chat error: %s",
                exc
            )
            return self._fallback_summary(
                conversation,
                memories
            )

        text = response["message"]["content"]
        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )

        if not match:
            return self._fallback_summary(
                conversation,
                memories
            )

        try:
            data = json.loads(
                match.group()
            )
        except json.JSONDecodeError:
            return self._fallback_summary(
                conversation,
                memories
            )

        topic = str(data.get("topic", "")).strip()
        summary = str(data.get("summary", "")).strip()
        importance = int(data.get("importance", 0) or 0)
        confidence = float(data.get("confidence", 0.0) or 0.0)

        if not topic or not summary or importance <= 0:
            return None

        return {
            "topic": topic,
            "summary": summary,
            "importance": importance,
            "confidence": max(0.0, min(confidence, 1.0))
        }
