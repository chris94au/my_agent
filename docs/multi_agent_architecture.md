# Multi-Agent Architecture

Generation 4 erweitert den bestehenden lokalen Agenten zu einer modularen Multi-Agent-Plattform, ohne die bisherigen Schnittstellen zu brechen.

## Overview

```text
User
  |
  v
Agent API
  |
  v
Orchestrator
  |
  v
Agent Router
  |
  +-----------------------------+
  |                             |
  v                             v
Planner Agent             Research Agent
Coding Agent              Memory Agent
Knowledge Agent           Vision Agent
Critic Agent              Task Agent
  |                             |
  +-----------------------------+
  |
  v
Execution Engine
  |
  v
Tools / Memory / Knowledge / Research
  |
  v
Final Response
```

## Core building blocks

### `agents/base_agent.py`
Defines the shared agent interface:

- `name`
- `role`
- `description`
- `system_prompt`
- `capabilities`
- `allowed_tools`
- `execute()`

### `agent_registry.py`
Central registry for:

- available agents
- capabilities
- versions
- allowed tools
- priorities

### `orchestrator.py`
The control plane that:

- analyzes incoming tasks
- asks the router which agents are needed
- runs agents sequentially or in parallel
- merges intermediate results
- prepares the final response

### `agent_router.py`
Chooses the agent set automatically from the task text and context.

### `context_bus.py`
Shared communication channel between agents. It stores:

- shared state
- intermediate results
- tool results
- sources
- memory context
- agent reports
- event history

## Specialized agents

- `planner_agent` – task decomposition, dependencies, priorities, agent selection
- `research_agent` – web research, source ranking, citation tracking
- `memory_agent` – retrieval, normalization, consolidation, archive management
- `knowledge_agent` – RAG, document search, retrieval, source evaluation
- `coding_agent` – code generation, analysis, refactoring, tests, docs
- `critic_agent` – validation of facts, logic, completeness, tool usage, sources
- `vision_agent` – image analysis, OCR, screenshots, diagrams
- `task_agent` – long-running tasks, status, resume, priorities

## Communication flow

1. The user sends a message to the Agent API.
2. The orchestrator creates a context snapshot and asks the router for the right agents.
3. Specialized agents write results into the context bus.
4. The execution engine uses the accumulated context to produce the final answer.
5. The critic validates the result and can request revision.

## Permission model

Each agent carries its own permission policy.

- Research agents are allowed to use research-oriented tools and denied filesystem/scheduler actions.
- Coding agents are allowed to use code editing tools and denied sensitive actions.
- The registry stores the permissions together with the agent metadata.

## Extensibility

The architecture is designed so future generations can add:

- plugins
- autonomous background workflows
- new specialist agents
- alternative routers
- stronger parallel scheduling
- new security policies

without changing the core interaction model.
