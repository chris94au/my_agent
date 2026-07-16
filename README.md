# my_agent

Ein lokaler Python-AI-Agent mit Memory, Embeddings, Tool-Aufrufen und Internetrecherche.

## Start

```bash
python3 main.py
```

Der Agent nutzt lokal:

- `qwen2.5:7b` für Chat, Memory-Extraktion, Validator und Zusammenfassungen
- `nomic-embed-text` für Embeddings
- SQLite für persistentes Memory

## Architektur

Die aktuelle Architektur ist auf Erweiterbarkeit statt auf einen großen Umbau ausgelegt:

- **Agent-Kern** in `agent.py`
- **Planner** in `planner.py` für mehrschrittige Aufgaben
- **Execution Loop** in `execution_loop.py` für Tool-Aufrufe und Antwortsynthese
- **Critic** in `critic.py` für Reflexion nach der Ausführung
- **Tool Registry** in `tools/registry.py` mit Berechtigungen, Parametervalidierung und Audit-Logging
- **Prompt-Verwaltung** in `prompts.py`
- **Tool-System** in `tools/`
- **Memory-Pipeline** mit Extraktion, Normalisierung, Validierung, Speicherung und Retrieval
- **Zusammenfassungen** als eigene Memory-Ebene neben Fakten
- **Internetrecherche** über `web_search` und `read_url`

## Memory-Pipeline

```text
User Input
  |
  v
LLM Response
  |
  v
Memory Extractor
  |
  v
Memory Normalizer
  |
  v
Memory Validator
  |
  v
Memory Storage
```

Zusätzlich erzeugt der Agent Gesprächszusammenfassungen, damit langfristiger Kontext gespeichert werden kann.

## Speicherebenen

### Fakten

Einzelfakten mit:

- `category`
- `key`
- `value`
- `importance`
- `confidence`
- Zeitstempel
- Embedding

### Zusammenfassungen

Separat gespeicherte Gesprächskontexte mit:

- `topic`
- `summary`
- `importance`
- `confidence`
- Zeitstempel
- Embedding

### Archive

Statt sofort zu löschen werden schwächere Einträge in den Archiv-Status verschoben. Wichtige Erinnerungen bleiben aktiv.

## Retrieval und Reflexion

Die Relevanz wird nicht nur über Embedding-Ähnlichkeit berechnet, sondern kombiniert:

- Similarity
- Importance
- Confidence
- Recency
- Nutzungshistorie

Der Agent nutzt Memory auch beim Planen und bei der Reflexion nach der Ausführung. Reflections werden als eigene Summary-Memory unter `execution_reflection` gespeichert.

Damit bleiben alte, aber wichtige Erinnerungen sichtbar.

## Tests

Automatisierte Tests liegen unter `tests/` und können mit `unittest` ausgeführt werden:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## Projektdateien

- `agent.py` – Orchestrierung des Agenten
- `memory.py` – SQLite-basierte Memory-Schicht
- `normalizer.py` – deterministische Normalisierung von Kategorien, Schlüsseln und Texten
- `memory_validator.py` – Qualitäts- und Vertrauensbewertung für Memories
- `memory_extractor.py` – Extraktion strukturierter Memory-Kandidaten aus Gesprächen
- `conversation_summarizer.py` – langfristige Gesprächszusammenfassungen
- `tools/` – lokale Tools, inklusive Websuche und Dateioperationen
- `tests/` – automatisierte Tests für Memory und Pipeline

## Aktueller Stand

Das Projekt ist ein laufend ausgebauter lokaler Agent. Der Fokus liegt aktuell auf:

- stabiler Memory-Konsolidierung
- Vertrauensbewertung
- Archivierung statt harter Löschung
- besserem Retrieval für den Prompt-Kontext
- sicherer Internetrecherche
