---
description: Create a ticket run from a local epic ticket, a Shortcut story, a Jira issue, or inline text
argument-hint: <epic-ticket-name | shortcut id/url | jira key/url | text> [--domain <name>] [--domains a,b]
---

Create a ticket run from `$ARGUMENTS`. This command only creates the run via `ai_run.py init`; it never starts the workflow (use `/start-ticket`).

## Rules

- No arguments → print usage `/create-ticket <source> [--domain <name>] [--domains a,b]` and stop; create nothing.
- Domain flags and input-declared domains follow the Domain step below; with no valid domain, omit `--domain` (the runner applies `default_domain`).
- Never overwrite an existing run: `init` unconditionally overwrites `input.md` and resets `status.json`, so you MUST check existence first.
- Every derived ID must pass `python .ai/bin/ai_wrap.py validate-id <ID>` (exit 0) before `init`.
- Never stage, commit, or push with git. Do not write run files yourself; only `ai_run.py init` creates them.

## Resolve the source (first match wins)

1. **Local epic ticket**: the argument is a file name/stem/slug matching `.ai/epics/*/breakdown/tickets/<name>*.md`.
   - Several matches (including the same stem under two epics) → list them and ask which one; never pick silently.
   - Run id = `<file stem>` (the matched ticket file name without `.md`), with no epic directory prefix. This command creates the correctly named run itself; it never calls or depends on `epic-generate-tickets`.
   - If `.ai/runs/<id>/input/input.md` exists and is non-empty: do nothing, report "run `<id>` already exists; use `/start-ticket <id>`". If the operator is trying a different content for an existing id, ask (use existing / new ID); never overwrite.
   - If only a run under `<EPIC-dir-name>-<file stem>` exists (made by an older version of this command), inform the operator and ask whether to use it or create the `<file stem>` run; create nothing silently.
   - Otherwise run the Finish `init` with the file content as the requirement.
2. **Shortcut**: `sc-<digits>`, or a URL containing `shortcut.com` and `/story/`.
3. **Jira**: `[A-Z][A-Z0-9]+-<digits>`, or a URL containing `atlassian.net/browse/`.
4. **Bare number** (e.g. `1234`): ask the operator "Shortcut or Jira?"; create nothing until answered.
5. **Anything else**: inline text. Ask the operator for the ticket ID (kebab-case), then use the text as the requirement.

## Domain (after the source is resolved, before `init`)

- Precedence: operator `--domains a,b` (ordered, first = primary) or single `--domain x` > domain declared in the input > omit.
- Declared in the input means an explicit declaration only: for a local epic ticket the `## Domains` section (first entry = primary; bullets or a comma list, backticks stripped; legacy `## Domain` accepted); for Shortcut/Jira/inline text a line such as `Domain: x` / `Domains: x, y`, or a label/field clearly naming a domain. Never guess from file paths or prose.
- Valid values are the keys of `domains` in `.ai/project_config.json`, matched case-insensitively. Warn about and drop unknown values; if none remain, omit `--domain`. Domain problems never block creation.
- If both `--domain` and `--domains` are given and `--domain` differs from the first of `--domains`, ask.
- One valid domain → `--domain <d>`. Several → `--domain <first> --domains <a,b>` (full ordered list).

## Shortcut / Jira (resolved lazily at runtime)

Only when the source needs it, use ToolSearch to discover MCP tools for that system (search for tool names mentioning "shortcut" or "atlassian"/"jira"). Do not assume exact tool names.

- No matching tool found → stop with an explicit error: which source, that the MCP server is not installed/configured, how to set it up (add the MCP server for that system to Claude Code and authenticate). Create nothing.
- Tool found but the call fails (auth, unreachable, not found) → stop with an explicit error: which source, which step failed, the original error text. Create nothing. No silent fallback to inline text; the operator may re-invoke with text.
- Compose `input.md` from the fields actually available: source URL/ID on the first line, then title, description, acceptance criteria (if present), links. Keep URLs verbatim (Figma links are auto-detected by the runner). Do not invent fields.
- Ticket ID = slugified `<KEY>-<title>` (kebab-case, truncated to fit 80 chars).
- Show the composed input, the ID and the detected domain(s) to the operator and ask for confirmation before `init`.

## Finish

Run `python .ai/bin/ai_wrap.py validate-id <id>`, then `python .ai/bin/ai_run.py init <id> "<text>" [--domain <d>] [--domains a,b]`. Report the ticket ID and the applied domain(s) (`domain=<d>`, or the `default_domain` fallback) and end with `Start with: /start-ticket <id>`.
