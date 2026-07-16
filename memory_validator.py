import json
import logging
import re

import ollama


logger = logging.getLogger(__name__)


class MemoryValidator:


    def __init__(self, model="qwen2.5:7b"):

        self.model = model


    def _conversation_excerpt(self, conversation, limit=3500):
        if not conversation:
            return ""

        text = str(conversation).strip()
        if len(text) <= limit:
            return text

        return text[-limit:]


    def _fallback_confidence(self, memory, conversation):
        text = (conversation or "").casefold()
        value = str(memory.get("value", "")).casefold()
        key = str(memory.get("key", "")).casefold()

        confidence = 0.55

        if value and value in text:
            confidence += 0.25

        if key and key in text:
            confidence += 0.1

        hedge_words = (
            "vielleicht",
            "eventuell",
            "wahrscheinlich",
            "glaube",
            "scheint",
            "könnte",
            "maybe",
            "perhaps",
            "probably"
        )

        if any(word in text for word in hedge_words):
            confidence -= 0.15

        return max(0.1, min(confidence, 1.0))


    def validate(self, memory, conversation=None):

        excerpt = self._conversation_excerpt(
            conversation
        )

        prompt = f"""
Du bist ein Memory-Validator.

Entscheide, ob diese Information dauerhaft
über den Benutzer gespeichert werden sollte.

Speichere nur Informationen, die:
- langfristig stabil sind
- zukünftige Antworten verbessern
- etwas über Fähigkeiten, Interessen,
  Projekte oder Präferenzen aussagen

Verwerfen:
- aktuelle Stimmung
- einmalige Ereignisse
- Wetter
- temporäre Aktivitäten
- zufällige Aussagen

Bewerte außerdem die Vertrauenswürdigkeit:
- direkte Aussagen des Benutzers: hohe confidence
- unsichere oder nur abgeleitete Informationen: niedrigere confidence

Kontext:
{excerpt}

Information:
{json.dumps(memory, ensure_ascii=False)}

Antworte ausschließlich mit JSON.

Wenn speichern:
{{
    "approved": true,
    "importance": 1-10,
    "confidence": 0.0-1.0
}}

Wenn nicht speichern:
{{
    "approved": false,
    "confidence": 0.0-1.0
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
                "Memory validation fallback due to chat error: %s",
                exc
            )
            return {
                "approved": True,
                "importance": int(memory.get("importance", 5)),
                "confidence": self._fallback_confidence(memory, conversation)
            }

        text = response["message"]["content"]

        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )

        if not match:
            return {
                "approved": True,
                "importance": int(memory.get("importance", 5)),
                "confidence": self._fallback_confidence(memory, conversation)
            }

        try:
            data = json.loads(
                match.group()
            )
        except json.JSONDecodeError:
            return {
                "approved": True,
                "importance": int(memory.get("importance", 5)),
                "confidence": self._fallback_confidence(memory, conversation)
            }

        if "confidence" not in data or data["confidence"] is None:
            data["confidence"] = self._fallback_confidence(memory, conversation)

        if data.get("approved", False):
            data["importance"] = int(data.get("importance", memory.get("importance", 5)))

        return data
