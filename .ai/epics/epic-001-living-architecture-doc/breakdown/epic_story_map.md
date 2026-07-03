# Epic Story Map — EPIC-001 Living Architecture Doc (Context Vault)

Repo-internal, machine-maintained architecture doc under `.ai/vault/`, injected token-capped into every agent prompt and kept fresh by the workflow itself.

Breakdown follows the design's Sequencing Strategy (§8): read path is independently shippable and risk-free; the write path builds on it. All work lands in the single `workflow` domain.

---

## Workstreams

### WS-A — Vault Foundation (read path)

Establishes the data layout and the always-on injection. Independently shippable; vault-less projects stay unchanged.

| ID | Title | Order | Depends on |
|----|-------|-------|------------|
| US-001 | Vault skeleton + templates + install copy | 1 | — |
| US-002 | Vault config block + prompt injection (read path) | 2 | US-001 |

### WS-B — Bootstrap & Migration

One-time seeding from the codebase and existing CLAUDE.md prose.

| ID | Title | Order | Depends on |
|----|-------|-------|------------|
| US-003 | `arch-init` two-phase + CLAUDE.md migration | 3 | US-001, US-002 |

### WS-C — Write Path (self-maintenance)

Keeps the vault fresh by process as tickets and epics land.

| ID | Title | Order | Depends on |
|----|-------|-------|------------|
| US-004 | Developer `## Architecture Impact` section + `dev-complete` check | 4 | — (sequenced after US-002) |
| US-005 | Distill stage: distiller role + subcommands + cap enforcement | 5 | US-002, US-004 |
| US-006 | ADR lifecycle: epic ADR distill + ticket-land flips | 6 | US-005 |

### WS-D — Drift Detection

| ID | Title | Order | Depends on |
|----|-------|-------|------------|
| US-007 | `arch-refresh` drift-check command | 7 | US-002, US-003 |

---

## Dependency Graph

```
US-001 ──► US-002 ──► US-003 ──► US-007
              │                    ▲
              ▼                    │
           US-004 ──► US-005 ──► US-006
```

- US-002 is the hinge: both bootstrap (US-003) and the write path (US-005) build on the readers/config it adds.
- US-004 is only loosely coupled (role + verification change); sequence it after US-002 so the developer prompt already carries vault context, and before US-005 which consumes its output.
- US-007 needs a populated vault (US-003) and the underscore-exclusion behavior from US-002.

---

## Suggested Execution Order

1. US-001 — vault skeleton + templates
2. US-002 — config + injection read path
3. US-003 — arch-init + CLAUDE.md migration
4. US-004 — developer Architecture Impact section
5. US-005 — distill write path
6. US-006 — ADR lifecycle
7. US-007 — arch-refresh drift check

Steps 1–2 ship independently and carry zero backward-compat risk. Steps 3–7 layer the bootstrap, write path, and drift detection on top.
