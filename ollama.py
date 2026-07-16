from __future__ import annotations

import json
import math
import re
from collections import Counter


STOPWORDS = {
    "und", "oder", "der", "die", "das", "ein", "eine", "ist", "sind", "ich", "du", "wir", "ihr", "sie",
    "the", "and", "or", "a", "an", "is", "are", "to", "of", "for", "with", "in", "on", "what", "which",
}



def _tokenize(text):
    return [
        token.lower()
        for token in re.findall(r"[\wÄÖÜäöüß]+", str(text), flags=re.UNICODE)
        if token
    ]



def _extract_last_section(text, markers):
    for marker in markers:
        idx = str(text).rfind(marker)
        if idx >= 0:
            return str(text)[idx + len(marker) :].strip()
    return str(text).strip()



def _response_from_prompt(prompt: str):
    prompt = str(prompt)
    lowered = prompt.casefold()

    if "antworte ausschließlich mit json" in lowered or "schema:" in lowered:
        if "planner" in lowered or "plan" in lowered:
            user_input = _extract_last_section(prompt, ["Benutzeranfrage:", "User:"])
            goal = user_input.splitlines()[0][:120] if user_input else "Aufgabe ausführen"
            if any(token in lowered for token in ("research", "recherch", "quelle", "quellen", "welche", "bestbewertet", "bewertet")):
                steps = [
                    {"action": "research", "input": user_input, "description": "Mehrquellen-Recherche durchführen"},
                    {"action": "respond", "description": "Ergebnis zusammenfassen"},
                ]
            else:
                steps = [
                    {"action": "analyze", "description": "Inhalt analysieren"},
                    {"action": "respond", "description": "Antwort formulieren"},
                ]
            return {"message": {"content": json.dumps({"goal": goal, "steps": steps}, ensure_ascii=False)}}

        if "critic" in lowered or "review" in lowered or "reviewer" in lowered:
            return {
                "message": {
                    "content": json.dumps(
                        {
                            "verdict": "pass",
                            "summary": "Die Ausführung ist konsistent.",
                            "risks": [],
                            "improvements": [],
                            "confidence": 0.8,
                            "should_retry": False,
                        },
                        ensure_ascii=False,
                    )
                }
            }

        if "validator" in lowered:
            return {
                "message": {
                    "content": json.dumps(
                        {
                            "approved": True,
                            "importance": 6,
                            "confidence": 0.8,
                        },
                        ensure_ascii=False,
                    )
                }
            }

        if "summary" in lowered or "summarizer" in lowered:
            return {
                "message": {
                    "content": json.dumps(
                        {
                            "topic": "allgemeines Gespräch",
                            "summary": _extract_last_section(prompt, ["Conversation:", "Gespräch:", "User:"])
                            [:200],
                            "importance": 5,
                            "confidence": 0.7,
                        },
                        ensure_ascii=False,
                    )
                }
            }

        if "extractor" in lowered or "extrahiere" in lowered:
            return {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "Extrahierte Informationen.",
                            "confidence": 0.7,
                            "facts": [],
                        },
                        ensure_ascii=False,
                    )
                }
            }

    if "beantworte die ursprüngliche anfrage" in lowered or "normalem text" in lowered:
        user_input = _extract_last_section(prompt, ["Benutzeranfrage:", "User:", "Frage:"])
        if not user_input:
            user_input = _extract_last_section(prompt, ["Query:"])
        return {
            "message": {
                "content": f"Ich habe die Anfrage bearbeitet: {user_input[:240] or 'Ergebnis bereit.'}"
            }
        }

    if "research summary" in lowered:
        return {"message": {"content": "Research Summary:\n- Relevante Quelle gefunden."}}

    last_user = _extract_last_section(prompt, ["Benutzeranfrage:", "User:", "Frage:", "Query:"])
    if last_user:
        return {"message": {"content": f"Antwort auf: {last_user[:240]}"}}
    return {"message": {"content": "{}"}}



def chat(model, messages):
    content = messages[-1]["content"] if messages else ""
    return _response_from_prompt(content)



def embeddings(model, prompt):
    tokens = _tokenize(prompt)
    if not tokens:
        return {"embedding": [0.0, 0.0, 0.0]}

    counts = Counter(token for token in tokens if token not in STOPWORDS)
    total = sum(counts.values()) or 1
    values = [
        min(1.0, len(tokens) / 100.0),
        min(1.0, len(counts) / 30.0),
        min(1.0, sum(counts.values()) / 50.0),
    ]
    return {"embedding": values}
