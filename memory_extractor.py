import ollama
import json
import re


class MemoryExtractor:


    def __init__(self, model="qwen2.5:7b"):

        self.model = model



    def extract(self, conversation):


        prompt = f"""
Du bist ein Memory-Extraktionssystem.

Deine einzige Aufgabe ist es, langfristig nützliche Informationen
über den Benutzer zu erkennen.

Eine Information ist speicherwürdig, wenn sie später Antworten
persönlicher oder hilfreicher machen kann.

Speichere insbesondere:

- Programmiersprachen
- Werkzeuge und Software
- Projekte
- Fähigkeiten
- Interessen
- bevorzugte Arbeitsweisen
- Ziele
- wiederkehrende Gewohnheiten

Verwende ausschließlich deutsche Schlüsselwörter für die Kategorien und Schlüssel.

Beispiele:

Eingabe:
"Ich programmiere hauptsächlich mit Python."

Ausgabe:
Format:

[
    {{
        "category": "skill",
        "key": "programming_language",
        "value": "Python",
        "importance": 8
    }}
]


Wenn mehrere Informationen vorhanden sind,
erstelle mehrere Einträge:

[
    {{
        "category": "...",
        "key": "...",
        "value": "...",
        "importance": 1-10
    }},
    {{
        "category": "...",
        "key": "...",
        "value": "...",
        "importance": 1-10
    }}
]


Eingabe:
"Hallo, wie geht es dir?"

Ausgabe:
{{}}


Regeln:

- Antworte ausschließlich mit JSON.
- Keine Erklärungen.
- Keine Markdown-Codeblöcke.
- Wenn mindestens eine nützliche Information vorhanden ist,
  MUSST du sie speichern.


Unterhaltung:

{conversation}
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

        print("EXTRACTOR RAW:")
        print(text)

        match = re.search(
            r"(\[.*\]|\{.*\})",
            text,
            re.DOTALL
        )


        if not match:

            return None


        try:

            data = json.loads(
                match.group()
            )

            if isinstance(data, dict):

                return [data]


            if isinstance(data, list):

                return data


            return None


        except:

            return None