import ollama
import json
import re


class MemoryValidator:


    def __init__(self, model="qwen2.5:7b"):

        self.model = model



    def validate(self, memory):


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


Information:

{json.dumps(memory, ensure_ascii=False)}


Antworte ausschließlich mit JSON.

Wenn speichern:

{{
    "approved": true,
    "importance": 1-10
}}

Wenn nicht speichern:

{{
    "approved": false
}}
"""


        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role":"user",
                    "content":prompt
                }
            ]
        )


        text = response["message"]["content"]


        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )


        if not match:

            return None


        try:

            return json.loads(
                match.group()
            )


        except:

            return None