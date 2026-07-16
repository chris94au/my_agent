# my_agent

Ein lokaler Python-AI-Agent mit Memory, Embeddings, Tool-Aufrufen und Internetrecherche.

## Start

Konsolenmodus:

```bash
python3 main.py
```

Desktop-GUI:

```bash
python3 main.py --gui
```

Der Agent nutzt lokal:

- `qwen2.5:7b` für Chat, Memory-Extraktion, Validator und Zusammenfassungen
- `nomic-embed-text` für Embeddings
- SQLite für persistentes Memory
- PySide6 für die native Desktop-GUI

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
- **Internetrecherche** über `web_search`, `web_fetch` und `read_url`
- **Research Pipeline** in `research/` für Quellenbewertung, Extraktion, Synthese und Zitationen
- **Multi-Agent-Plattform** mit `orchestrator.py`, `agent_router.py`, `context_bus.py` und spezialisierten Agenten in `agents/`

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

## Research-Architektur

Der Agent arbeitet bei Research-Anfragen nicht nur mit Suchergebnissen, sondern mit einer mehrstufigen Research-Pipeline:

1. `web_search` findet mögliche Quellen.
2. `research/source_ranker.py` bewertet Quellen nach Zuverlässigkeit, Relevanz und Vollständigkeit.
3. `web_fetch` ruft den Seiteninhalt ab.
4. `research/html_parser.py` bereinigt HTML und extrahiert lesbaren Text.
5. `research/extractor.py` extrahiert strukturierte Fakten aus den Quellen.
6. `research/synthesizer.py` führt mehrere Quellen zu einem konsistenten Research-Context zusammen.
7. `research/citations.py` verfolgt Claims und Quellen.
8. `research/memory_integration.py` speichert nur langfristig relevante Erkenntnisse oder Benutzerpräferenzen.

Suchergebnisse sind nur Quellenhinweise, nicht die fertige Antwort.

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
- `tools/` – lokale Tools, inklusive Websuche, Web-Fetch und Dateioperationen
- `research/` – Research-Module für HTML-Bereinigung, Ranking, Extraktion, Synthese, Zitationen und Memory-Integration
- `tests/` – automatisierte Tests für Memory, Research und Pipeline

## Aktueller Stand

Das Projekt ist ein laufend ausgebauter lokaler Agent. Der Fokus liegt aktuell auf:

- stabiler Memory-Konsolidierung
- Vertrauensbewertung
- Archivierung statt harter Löschung
- besserem Retrieval für den Prompt-Kontext
- sicherer Internetrecherche
