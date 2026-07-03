# Epic Design: Living Architecture Doc (Context Vault)

Design for a repo-internal, machine-maintained architecture doc under `.ai/vault/`, injected token-capped into every agent prompt and kept fresh by the workflow itself. This design resolves the open questions left by analysis and specifies where each change hooks into `.ai/bin/ai_run.py`.

---

## 1. Solution Overview

### High-level approach

Three orthogonal pieces, layered onto the existing `prepare → act → complete` runner:

1. **Vault (data)** — plain markdown under `.ai/vault/architecture/`: one small `system-overview.md`, per-domain `modules/<domain>.md`, and `decisions/ADR-NNN-*.md`. Single source of truth for architecture prose.
2. **Injection (read path)** — new `build_vault_context(domains)` helper feeds vault content into `build_role_prompt` / `build_epic_role_prompt` via the existing `build_project_context` seam. Overview always injected; module docs scoped to resolved domain(s); ADRs never auto-injected.
3. **Distill (write path)** — a full `prepare → act → complete` stage, same shape as architect/dev/review/qa, resolved automatically right after `qa-complete` (ticket, on `pass`) and `epic-review-complete` (epic, on `approve`) so the operator flow still feels seamless, but the `act` step stays human-in-loop like every other stage — `ai_run.py` has no mechanism to invoke an LLM synchronously (see D1, revised). It merges architecture deltas back into the vault under a hard line cap.

Two operator commands sit outside the loop: `arch-init` (two-phase: config bootstrap + vault seed, see D8) and `arch-refresh` (drift check).

### Architecture (data + control flow)

```
project_config.json (vault config, caps)
        │
        ▼
build_project_context ──► build_vault_context(domains) ──► reads .ai/vault/
        │                        (overview + scoped modules)
        ▼
build_role_prompt / build_epic_role_prompt ──► agent prompt (capped)
        │
        ▼  agent acts, developer writes ## Architecture Impact
        ▼
qa-complete (pass) ──► distill-prepare (auto) ──► [human pastes] ──► distill-complete
                        writes prompt file;         distill agent       verifies caps,
                        --run-auto spawns pane       rewrites vault      blocks over-cap (D5)

epic-review-complete  ──► adr-distill-prepare (auto) ──► [human pastes] ──► adr-distill-complete
(approve)                  writes ADR prompt             writes proposed     verifies ADR
                                                          ADR(s)              frontmatter
```

Everything degrades to a no-op when `.ai/vault/` is absent — existing projects are untouched.

---

## 2. Key Design Decisions

### D1 — Distill hook point: new `distill-prepare`/`distill-complete` stage, auto-triggered on QA pass (revised after review)

**Decision (revised):** distill is a **full new stage**, not an internal sub-step of `qa-complete`. `distill-prepare` and `distill-complete` are new CLI subcommands, registered in `KNOWN_SUBCOMMANDS` and `sub.add_parser` exactly like `dev-prepare`/`dev-complete`. They follow the same manual-`act` pattern as every other stage: `distill-prepare` (deterministic Python, no LLM call) writes `distill/distill_prompt.md`; a human pastes it into a Claude session (or it is auto-pasted via `spawn_ai_wezterm` under `--run-auto`, same as `dev-prepare`); `distill-complete` verifies the resulting vault files and caps.

**What changed and why:** the prior decision said distill "runs prepare → act → verify internally" as a sub-step of `qa_complete`, implying `qa_complete` could itself invoke and block on an LLM. Review flagged that `ai_run.py` has **no mechanism to invoke an LLM synchronously** — confirmed by inspection: every agent interaction goes through `spawn_ai_wezterm` (interactive WezTerm pane spawn + keystroke injection, `ai_run.py:2621`) or a human pasting a prompt by hand; `ENGINE_REGISTRY` (`ai_run.py:32-41`) only defines interactive launch commands (no `anthropic` SDK call, no headless `claude -p`/`--print` subprocess). `qa_complete` itself (`ai_run.py:1706-1722`) only reads/validates a JSON report a human already produced. Building a new synchronous headless-invocation mechanism (API key handling, output capture) is out of scope for this epic — see §7 — so distill must be a real, human-in-loop stage like the rest of the pipeline.

**Revised mechanics:**
- `qa_complete`, on `decision == "pass"`, keeps doing what it does today (verify report, build fix context) **and** additionally calls `distill_prepare(ticket)` automatically — safe because `distill_prepare` is pure Python (no LLM), the same kind of in-process call `build_qa_fix_context` already makes inside `qa_complete` (`ai_run.py:1718`).
- `distill-prepare` is added to `_PREPARE_STEP_PROMPT` / `_PREPARE_TO_COMPLETE` (`ai_run.py:2592-2610`) and to the ticket stage router (`next_action`, `ai_run.py:2458-2564`), so `next` / `next --run-auto` resolves to it immediately after a passing `qa-complete` and spawns a WezTerm pane exactly the way `dev-prepare` does today.
- The human pastes/presses Enter like every other stage; the distill agent rewrites the vault; `distill-complete` (human-run, or chained via `next --run`) then verifies caps and ADR frontmatter.
- On QA `fail`, `distill_prepare` is not invoked; the existing fix loop runs, and distill happens on the eventual passing `qa-complete`.
- Symmetric for epics: `epic-review-complete`, on `approve`, auto-calls `adr_distill_prepare(epic)`; `epic-next` / `--run-auto` resolves to `adr-distill-prepare` the same way; `adr-distill-complete` verifies.

**Trade-off accepted:** this reintroduces the stage-count growth the original decision tried to avoid — `KNOWN_SUBCOMMANDS`, the stage sequence, and `next`/`epic-next` resolution each gain two new steps. That cost is smaller and more honest than an unspecified automation mechanism: every other stage already pays it, and the operator experience is unchanged (`next --run-auto` still auto-advances and auto-spawns panes; the human still just presses Enter at each step).

### D2 — Distill is its own role file, reusing the architect skill set

**Decision:** new `.ai/agents/distiller.md` role, but it loads the **architect** domain skills (same pattern `architect_reviewer` already uses at `ai_run.py:707`).

**Rationale:** distilling ("what must an agent know to not make a wrong decision here?") is a distinct instruction from designing a ticket — a shared prompt would bloat both. A dedicated file keeps the cap rule, the "map not encyclopedia" rule, and the prune rule in one place. Skill reuse avoids duplicating domain skill config.

### D3 — Injection breadth: overview to all; module docs to architect + developer only

**Decision:** `system-overview.md` injects into every role (ticket + epic). `modules/<domain>.md` injects only for **architect** and **developer** (ticket) and **epic_analyst** + **epic_designer** (epic). Reviewer/QA/epic_reviewer/epic_planner get overview only.

**Rationale:** reviewers and QA judge a diff against acceptance criteria; they need the system map (overview) but rarely the full module deep-dive, which is the largest injected payload. Restricting modules to the roles that *produce* design/code keeps token regression bounded. This is config-driven (see D6) so a project can opt reviewer/QA in.

### D4 — ADR numbering: scan-max + zero-pad, allocated at write time

**Decision:** `ADR-NNN` = `max(existing NNN in decisions/) + 1`, zero-padded to 3 digits, computed by a helper `next_adr_id()` at the moment the distill agent is told to create one. IDs are never reserved ahead of time.

**Rationale:** concurrent epics/tickets are rare in this single-operator workflow, and allocation-at-write-time with a filesystem scan is simple and collision-free for sequential runs. The runner passes the next free ID into the distill prompt so the agent does not guess. Concurrent-run collisions are an accepted low risk (see §6).

### D5 — Module-doc cap: configurable, softer than overview; overview cap has a defined terminal state (revised after review)

**Decision:** module docs get their own line cap (default 400) checked in `distill-complete`, same mechanism as the overview cap (default 200).

- **Module cap over limit:** `distill-complete` re-runs `distill-prepare` once with an added compress instruction (human pastes again); still over → warn in the completion output and proceed. Non-fatal — module docs are domain-scoped, so a persistently long one is a quality problem, not a correctness one.
- **Overview cap over limit (previously undefined — fixed):** `distill-complete` re-runs `distill-prepare` once with a compress instruction, same as modules. If still over cap after that single retry, `distill-complete` **does not mark the stage complete**. It writes `fix/vault_cap_exceeded.md` (what's over, by how many lines, which sections are largest) and leaves the ticket parked on `distill-complete` — the same shape as a `request_changes`/`fail` decision parking a ticket on its fix loop today. A human manually trims `system-overview.md` under the cap (or raises `overview_cap_lines` in config, an explicit opt-in) and re-runs `distill-complete`. No silent proceed, no unbounded auto-retry.

**Rationale:** the overview cap is load-bearing (injected into every role prompt), so it must never silently blow past budget the way an unbounded retry loop or a silent warn-and-proceed would allow. One bounded auto-retry catches the common case (agent verbosity); the block-until-human-fixes path reuses the fix-loop shape the workflow already has, so it needs no new mental model. Modules are domain-scoped and non-load-bearing everywhere, so a softer warn-and-proceed is acceptable there.

### D6 — Config-driven with zero-config defaults

**Decision:** all knobs live under a new optional `vault` block in `project_config.json`; absence = disabled-but-safe defaults. No existing project must edit config to keep working.

```jsonc
"vault": {
  "enabled": true,                 // false or absent + no vault dir → full no-op
  "path": ".ai/vault",             // override root
  "overview_cap_lines": 200,
  "module_cap_lines": 400,
  "inject_modules_for": ["architect", "developer",
                         "epic_analyst", "epic_designer"]
}
```

`enabled` defaults to `true` only when the vault directory exists; a project with no `.ai/vault/` behaves exactly as today regardless of config.

### D7 — Multi-domain: union for epics, single for tickets, dedup on inject

**Decision:** tickets inject exactly one module doc (`get_ticket_domain`). Epics inject the union of module docs across `get_epic_domains`, deduped, mirroring how `build_epic_project_context` already unions paths (`ai_run.py:910`). No support for multi-domain tickets — resolution stays 1:1.

**Rationale:** matches existing domain-resolution contracts; no new resolution logic.

### D8 — `arch-init` is two-phase: config bootstrap (if missing), then vault bootstrap

**Decision:** `arch-init` runs two phases in sequence, each independently git-diff reviewable:

1. **Config bootstrap** (new, conditional) — if `project_config.json` has no `domains` block (a genuinely fresh project that only received the `.ai/` skeleton via the install script, with no project-specific config yet), an agent sweeps the repo to infer domain names, their `paths`, and per-role `skills` file lists, and writes `project_config.json`. Skipped entirely (no-op) when `domains` already exist — this phase never touches an already-configured project.
2. **Vault bootstrap** (original scope) — once domains are resolved (from phase 1's output or pre-existing config), generate `system-overview.md` + `modules/<domain>.md` per domain, then run the CLAUDE.md migration.

**Rationale:** the rest of this design assumes `project_config.json` domains already exist — they're load-bearing everywhere (`get_ticket_domain`/`get_epic_domains` drive routing for every role prompt, not just vault injection). For a project that only ran the install script (ships `.ai/bin`, `.ai/agents`, `.ai/templates` — never project-specific config), that assumption breaks: `arch-init` couldn't even decide which module docs to write. Splitting into phases keeps the higher-risk work — domain/skill inference, which misroutes every future ticket if wrong — as its own reviewable step instead of silently folding it into vault content generation, matching the existing "bootstrap edits are human-reviewed via git diff" pattern already used for the CLAUDE.md migration.

**Scope boundary:** phase 1 only writes `domains.<name>.paths` and `domains.<name>.skills.<role>` — pointing each role at existing skill files it finds (stack docs, conventions, etc.) or leaving the list empty (a valid, already-supported state). It does not author new skill *file content* from scratch; a domain that needs bespoke skill material stays a human follow-up. This closes a pre-existing gap in the workflow's own project-onboarding path (domain/skill config was always needed, even without vault) — this epic closes it here because `arch-init` is the first agent pass a fresh project runs anyway.

---

## 3. Component Breakdown

All changes concentrate in `.ai/bin/ai_run.py`, `.ai/agents/`, `.ai/templates/`, and a new `.ai/vault/` skeleton.

### 3.1 Vault data (`.ai/vault/architecture/`)

| File | Purpose | Cap |
|---|---|---|
| `system-overview.md` | Components table (name, 1-line responsibility, entry-point path, module link), numbered data flows, invariants, ADR index | ~200 lines |
| `modules/<domain>.md` | Per-domain "how it works"; matches `project_config.json` domains | ~400 lines |
| `decisions/ADR-NNN-*.md` | Why/alternatives; frontmatter links epic + tickets | unbounded |

Templates for each shipped in `.ai/templates/vault/` and copied by the install/skeleton flow. Fixed section headings so distill and verification can target them.

### 3.2 Injection layer (`ai_run.py`)

- **`vault_root()`** — resolves configured path; returns `None` when vault disabled/absent.
- **`read_vault_overview()`** — returns overview text or `""` (graceful empty).
- **`read_vault_modules(domains, role)`** — returns concatenated module docs for the given domains **iff** role ∈ `inject_modules_for`, else `""`; dedups across domains.
- **`build_vault_context(domains, role)`** — assembles the `# Architecture (Vault)` prompt section; returns `""` when nothing to inject (section omitted entirely).
- Wire into `build_role_prompt` (after `# Project Context`, before skills) and `build_epic_role_prompt` symmetrically. `build_project_context` stays unchanged in signature; injection is a sibling section so a missing vault never alters existing output.

### 3.3 Distill layer (`ai_run.py` + `.ai/agents/distiller.md`) — new CLI subcommands (revised, see D1)

- **`distill-prepare` / `distill_prepare(ticket)`** — new subcommand: registered in `KNOWN_SUBCOMMANDS` + `sub.add_parser`, added to `_PREPARE_STEP_PROMPT`. Builds a distill prompt: current overview + current domain module + developer `## Architecture Impact` + design_note delta + the next free ADR id. Writes to `.../distill/distill_prompt.md`. Invoked automatically as plain Python (not an LLM call) by `qa_complete` when `decision == "pass"`; resolved next by `next` / `next --run-auto` exactly like `dev-prepare` today.
- **`distill-complete` / `distill_complete(ticket)`** — new subcommand, added to `_PREPARE_TO_COMPLETE`. Verifies overview ≤ `overview_cap_lines` (bounded retry then human-block, see D5) and module ≤ `module_cap_lines` (soft), verifies ADR frontmatter well-formed. Human-invoked (or chained via `next --run`) after the human pastes the distill prompt into a Claude session, same as every other `*-complete`.
- **Epic ADR distill** — symmetric new subcommands `adr-distill-prepare` / `adr-distill-complete`. `epic_review_complete`, on `approve`, auto-calls `adr_distill_prepare(epic)` (pure Python) to build the prompt; a human pastes it to emit `proposed` ADR(s) from `epic_design.md` trade-offs, linked to the epic; `adr-distill-complete` verifies. Ticket land (`distill-complete`) flips `proposed → accepted` and appends the ticket id.

### 3.4 Operator commands (`ai_run.py`)

- **`arch-init`** — two-phase (see D8): (1) config bootstrap — conditional, only when `project_config.json` has no `domains`; sweeps repo, writes `domains.<name>.paths` + `domains.<name>.skills.<role>`; (2) vault bootstrap — codebase sweep + CLAUDE.md migration seed (see §4); writes initial overview + module docs per resolved domain. Registered in `KNOWN_SUBCOMMANDS` and `sub.add_parser`; both phases produce human-reviewed git diffs.
- **`arch-refresh`** — agent re-derives overview from code, diffs against current, writes the drift report to `.ai/vault/architecture/_drift_report.md` (leading underscore excludes it from injection readers; overwritten each run, reviewed via `git diff` like `arch-init` edits). Does not auto-overwrite `system-overview.md`; human applies changes manually.

### 3.5 Agent role updates (`.ai/agents/`)

- `developer.md` — mandate a `## Architecture Impact` section in `implementation_report.md` (`"none"` valid).
- `distiller.md` — new: cap rule, "map not encyclopedia" line test, ADR lifecycle, prune signal.
- `epic_designer.md` (this file's role) — note that approved trade-offs become `proposed` ADRs, so state alternatives-considered explicitly.

---

## 4. Data Flow

### 4.1 Read path (every run)

1. Runner calls `build_role_prompt(ticket, role, task)`.
2. `get_ticket_domain(ticket)` → domain.
3. `build_vault_context([domain], role)`: always overview; module doc iff role opted in.
4. Section appended to prompt (or omitted if vault empty). Agent starts with an accurate map instead of re-deriving.

### 4.2 Write path (ticket land)

1. Developer writes code + `## Architecture Impact` in `implementation_report.md`.
2. Review + QA pass.
3. `qa_complete` (on pass) auto-calls `distill_prepare` (pure Python) → writes `distill_prompt.md` → `next`/`next --run-auto` resolves to `distill-prepare` and spawns a pane like any other stage.
4. Human pastes the prompt; distill agent rewrites `system-overview.md` + `modules/<domain>.md`, updates ADR `tickets:` + flips `proposed → accepted`, prunes stale `planned` entries.
5. `distill-complete` enforces caps: over module cap → one auto-retry then warn-and-proceed; over overview cap → one auto-retry then block the stage until a human trims it (see D5).

### 4.3 Write path (epic approval)

1. `epic-review-complete` → `approve`, auto-calls `adr_distill_prepare` (pure Python) → `epic-next` resolves to `adr-distill-prepare`, spawns a pane.
2. Human pastes the prompt; distill agent writes trade-offs from `epic_design.md` into `proposed` ADR(s) linked to the epic; marks target module-doc entries `status: planned`.
3. `adr-distill-complete` verifies ADR frontmatter.
4. Implementing tickets later flip `planned → current` and ADR `proposed → accepted`.

### 4.4 Bootstrap path

`arch-init` (see D8):

1. **Phase 1 — config bootstrap** (only if `project_config.json` has no `domains`): sweep repo structure → infer domain names + `paths` + per-role `skills` file lists → write `project_config.json`. Human reviews via git diff before continuing. Skipped entirely if domains already exist.
2. **Phase 2 — vault bootstrap**: sweep code + parse `## Architecture` from root and `.ai/CLAUDE.md` → dedupe union → write overview (project-wide) + module docs (domain/stack detail, one per resolved domain) → replace root `## Architecture` with `@.ai/vault/architecture/system-overview.md` import → strip migrated sections from `.ai/CLAUDE.md`. All edits reviewed via git diff.

---

## 5. Integration Points

- **`project_config.json`** — new optional `vault` block; read via existing `load_project_config`. No schema break. For projects with no `domains` yet (fresh install-script-only setup), `arch-init` phase 1 (D8) writes `domains.<name>.paths` + `domains.<name>.skills.<role>` before vault content generation can resolve a domain.
- **Root `CLAUDE.md`** — gains `@.ai/vault/architecture/system-overview.md` import (interactive Claude sessions only; workflow prompts inject directly and do not depend on it).
- **`.ai/CLAUDE.md`** — workflow operating guide only after migration; architecture prose removed.
- **Git** — the diff surface for reviewing one-time `arch-init` edits.
- **LLM agents** — distill / `arch-init` / `arch-refresh` are agent-driven; no new third-party services, no RAG/embedding infra.
- **Obsidian** — viewer only; plain markdown, wikilinks optional.
- **CLI surface** — `distill-prepare` / `distill-complete` (ticket) and `adr-distill-prepare` / `adr-distill-complete` (epic) are new subcommands in `KNOWN_SUBCOMMANDS`, `sub.add_parser`, and the `next` / `epic-next` stage routers (see D1, revised).

---

## 6. Risks and Trade-offs

| Risk | Mitigation |
|---|---|
| Overview bloat over many tickets | Cap in distill prompt **and** verified in `distill-complete`; one bounded auto-retry, then the stage blocks for a human trim (see D5) — never silently proceeds over cap; adding a component requires pruning; new components get a link, not prose. |
| "Short but wrong" drift (cap can't catch) | `arch-refresh` re-derives from code and diffs; run periodically / on demand. |
| Stale `planned` entries from abandoned epics | Distill prune signal: `proposed` ADRs with zero tickets flag their `planned` module entries for removal. |
| Backward-compat breakage | `vault_root()` returns `None` when absent; all readers return `""`; section omitted. Verified by running the full pipeline on a vault-less project. |
| Token regression | Overview-only always-inject; modules scoped to architect/developer (+epic designer/analyst); ADRs never auto-injected; caps configurable. |
| ADR id collision under concurrent runs | Accepted low risk (single-operator workflow); scan-max allocation at write time. Sequential runs are collision-free. |
| Migration data loss / double-load | Dedup across both CLAUDE.md files; human git-diff review; distill never edits CLAUDE.md (only flags contradictions as a report note). |
| Distill quality degradation | Dedicated `distiller.md` with the explicit line test; `arch-refresh` as periodic corrective. |
| Wrong domain/skill inference on a fresh project (D8 phase 1) | Runs only when `domains` is absent (never touches configured projects); human reviews the `project_config.json` diff before phase 2 (vault) runs off it; phase 1 never authors new skill file content, only wires paths/existing files. |

**Trade-off accepted:** `distill-prepare` is only ever auto-triggered by a passing `qa-complete`, coupling vault freshness to the QA-pass path — a ticket abandoned before QA pass never distills. This is intended: only trusted, shipped work updates the map.

---

## 7. Out of Scope

- RAG / embedding retrieval — plain file injection only.
- Obsidian plugins, MCP servers, Obsidian-specific syntax requirements.
- Cross-project / global vault — vault is per-project, inside the repo.
- Injecting raw run history into prompts.
- Multi-domain **tickets** (resolution stays 1:1; only epics union module docs).
- Automatic overwrite by `arch-refresh` — it reports drift; humans apply.
- Concurrent-run ADR id locking / reservation.
- Authoring new skill *content* from scratch during `arch-init` phase 1 — it only wires existing files or leaves an empty list (D8); writing bespoke skill material stays a human follow-up.

---

## 8. Sequencing Strategy

1. **Vault skeleton + templates** — `.ai/vault/` structure, templates, install/skeleton copy. No behavior change.
2. **Config + injection (read path)** — `vault` config block, `vault_root`/readers, `build_vault_context`, wire into both prompt builders. Backward-compat verified (vault-less pipeline unchanged).
3. **`arch-init` + CLAUDE.md migration** — includes phase 1 config bootstrap (D8, conditional on missing `domains`) ahead of phase 2 vault seed; seed this repo as the reference case (already has `domains`, so phase 1 is a no-op here — validate phase 1 against a project without `project_config.json` domains separately); validate overview + module docs.
4. **Developer `## Architecture Impact` + verification** — role update + presence check in `dev-complete`.
5. **Distill (write path)** — `distiller.md`; new `distill-prepare`/`distill-complete` subcommands (registered in `KNOWN_SUBCOMMANDS`, stage router, `_PREPARE_STEP_PROMPT`/`_PREPARE_TO_COMPLETE`); `qa_complete` auto-triggers `distill_prepare` on pass; cap enforcement with bounded retry + human-block terminal state (D5).
6. **ADR lifecycle** — new `adr-distill-prepare`/`adr-distill-complete` subcommands, auto-triggered by `epic_review_complete` on approve; ticket-land flips via `distill-complete`; prune signal.
7. **`arch-refresh`** — drift check, last (depends on a populated vault).

Steps 1–2 are independently shippable and risk-free; the write path (4–6) builds on them.

---

## 9. Open Questions (for breakdown / execution)

- Exact distill prompt wording for the "would an agent make a wrong decision without this line?" test — tune against this repo.
- Whether `arch-refresh` should be schedulable (out of scope here, note for a follow-up epic).
- Precise `## Architecture Impact` schema (freeform vs. structured bullets) — decide in the developer-role ticket.
