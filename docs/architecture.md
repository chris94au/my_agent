# Architekturübersicht

## Ziele

Der Agent soll lokal laufen, Erinnerungen konsistent speichern und nur die relevantesten Kontexte in den Prompt aufnehmen.

Die aktuelle Architektur erweitert den bestehenden Kern gezielt statt ihn umzubauen.

## Hauptkomponenten

### 1. Agent-Kern

`agent.py` koordiniert:

- Chat mit dem Modell
- Tool-Aufrufe
- Memory-Extraktion
- Memory-Normalisierung
- Memory-Validierung
- Gesprächszusammenfassungen
- Speicherung in SQLite

### 2. Memory-Extractor

`memory_extractor.py` erkennt aus dem Gespräch langfristig nützliche Informationen.

### 3. Memory-Normalizer

`normalizer.py` mappt unterschiedliche Begriffe auf konsistente Schlüssel.

Beispiel:

- `musik_band`
- `musik_bands`
- `musik_bewerber`
- `band`

werden auf `Lieblingsband` normalisiert.

### 4. Memory-Validator

`memory_validator.py` entscheidet, ob ein Kandidat dauerhaft gespeichert wird, und bewertet zusätzlich:

- Importance
- Confidence

Direkte Aussagen bekommen hohe Confidence. Unsichere oder indirekte Aussagen bekommen geringere Confidence.

### 5. Memory-Speicher

`memory.py` speichert:

- Fakten
- Gesprächszusammenfassungen

beide mit Embeddings, Importance, Confidence und Status.

### 6. Conversation Summarizer

`conversation_summarizer.py` erzeugt langfristig nützliche Gesprächszusammenfassungen.

Diese ergänzen Fakten und ersetzen sie nicht.

### 7. Retrieval

Das Retrieval kombiniert mehrere Signale:

- Embedding Similarity
- Importance
- Confidence
- Recency
- Nutzungshäufigkeit

Damit werden die relevantesten Erinnerungen in den Prompt geladen.

### 8. Archive

Weniger relevante Erinnerungen werden nicht gelöscht, sondern archiviert.

Das schützt vor unkontrolliertem Wachstum und bewahrt historische Daten.

## Datenmodell

### facts

- category
- key
- value
- importance
- confidence
- status
- occurrence_count
- use_count
- timestamp
- last_seen_at
- last_used_at
- archived_at
- archive_reason
- embedding

### summaries

- topic
- summary
- importance
- confidence
- status
- occurrence_count
- use_count
- timestamp
- last_seen_at
- last_used_at
- archived_at
- archive_reason
- embedding

## Datenfluss

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
  |
  +--> Facts
  |
  +--> Conversation Summaries
  |
  v
Memory Retrieval
  |
  v
Prompt Context
```

## Retrieval-Strategie

Ein Eintrag wird anhand eines Endscores sortiert:

- Similarity
- Importance
- Confidence
- Recency
- Nutzungshistorie

Archivierte Einträge bleiben erhalten, werden aber niedriger gewichtet.

## Sicherheits- und Lebenszyklusregeln

- Keine sofortige Löschung
- Archivierung statt Entfernen
- Downloads aus dem Internet bleiben bestätigungspflichtig
- Webquellen werden dynamisch priorisiert

## Teststrategie

Die Tests prüfen:

- Normalisierung bekannter Synonyme
- Importance-Evolution bei Wiederholungen
- Confidence-Speicherung
- separate Speicherung von Fakten und Zusammenfassungen
- Archivierung statt Löschung
- Pipeline-Verhalten des Agenten
