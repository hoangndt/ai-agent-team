---
id: ADR-001
status: proposed
epic: ""
tickets: [US-008-create-custom-agent-for-this-workflow]
supersedes: ""
---

## Context

Operators want to drive the ticket/epic workflow from one Claude Code session (slash commands, per-stage sub-agents, MCP ticket sources) without changing the existing runner or WezTerm flow.

## Decision

Add a Claude orchestration layer (`.claude/commands`, `.claude/agents/workflow-step*.md`) that consumes routing JSON from a separate read-only sidecar `.ai/bin/ai_wrap.py` (wrapping `ai_run.next_action`/`epic_next_action`). The orchestrator calls explicit `ai_run.py <step>` names and confirms each complete from `status.json`. `ai_run.py` is not modified.

## Alternatives

- Extend `ai_run.py` with JSON/orchestration modes: rejected — risks the old flow, grows the single-file runner.
- Python driving `claude -p` per step: rejected — loses interactive gates and MCP access.
- Per-role `.claude/agents/*.md`: rejected — drifts from `.ai/agents/*.md`.
- Teaching runner Shortcut/Jira: rejected — network/auth deps in stdlib-only runner.

## Consequences

Old flow untouched and sidecar deletable. Sidecar depends on runner internals (`next_action`, prompt maps); renames break it. Orchestrator must re-verify state from `status.json` after every complete.
