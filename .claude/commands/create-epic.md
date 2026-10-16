---
description: Create an epic from inline text, a Shortcut epic/story, or a Jira epic/issue
argument-hint: <text | shortcut id/url | jira key/url> [--domains a,b]
---

Create an epic from `$ARGUMENTS`. This command only runs `ai_run.py epic-init`; it never starts the workflow (use `/start-epic`).

## Rules

- No arguments → print usage `/create-epic <source> [--domains a,b]` and stop; create nothing.
- `--domains a,b` is passed through to `epic-init` only if the operator gave it; otherwise omit it (the runner uses all configured domains).
- Never overwrite an existing epic: if `.ai/epics/<EPIC>/status.json` exists, report "epic exists; use `/start-epic <EPIC>`" (or ask for a new ID). `epic-init` overwrites `epic_input.md` and resets `status.json`.
- Every derived ID must pass `python .ai/bin/ai_wrap.py validate-id <EPIC>` (exit 0) before `epic-init`.
- Never stage, commit, or push with git. Do not write epic files yourself.

## Resolve the source

1. **Shortcut**: `sc-<digits>` or a URL containing `shortcut.com` (epic or story). 
2. **Jira**: `[A-Z][A-Z0-9]+-<digits>` or a URL containing `atlassian.net/browse/` (epic or issue).
3. **Bare number**: ask "Shortcut or Jira?"; create nothing until answered.
4. **Anything else**: inline text. Ask for the epic ID (e.g. `EPIC-001`).

For Shortcut/Jira, discover the MCP tools lazily with ToolSearch (names mentioning "shortcut" or "atlassian"/"jira"); never assume exact tool names. Fetch the parent item and, if the tools expose them, its child stories/issues; otherwise the parent only. No matching tool → explicit error (source, not installed/configured, setup hint) and create nothing. Call failure → explicit error with source, failing step, original error text; create nothing; no silent fallback.

Compose the requirement from the available fields (source URL/ID first, then title, description, child items, links; do not invent fields). Epic ID = `EPIC-<NNN>` next free number under `.ai/epics/` unless the source suggests a slug; ask the operator when unsure. Show the composed text and ID and ask for confirmation before `epic-init`.

## Finish

Run `python .ai/bin/ai_run.py epic-init <EPIC> "<text>" [--domains a,b]`. Report the epic ID and end with `Start with: /start-epic <EPIC>`.
