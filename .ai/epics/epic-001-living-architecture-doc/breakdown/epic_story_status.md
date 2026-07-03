# Epic Story Status — EPIC-001 Living Architecture Doc (Context Vault)

Epic: Repo-internal, machine-maintained architecture doc under `.ai/vault/`, injected token-capped into every agent prompt and kept fresh by the workflow itself.
Last updated: 2026-07-03 (US-005 done)

---

## Status Key

| Symbol | Meaning |
|--------|---------|
| ✅ | Done — merged to branch |
| 🔄 | In progress |
| ⬜ | Not started |

---

## WS-A — Vault Foundation (read path)

| ID | Title | Status | Branch | Report |
|----|-------|--------|--------|--------|
| US-001 | Vault skeleton + templates + install copy | ✅ | `EPIC-001-US-001-vault-skeleton-templates` | [report](.ai/runs/EPIC-001-US-001-vault-skeleton-templates/dev/implementation_report.md) |
| US-002 | Vault config block + prompt injection (read path) | ✅ | `EPIC-001-US-002-vault-injection-read-path` | [report](.ai/runs/EPIC-001-US-002-vault-injection-read-path/dev/implementation_report.md) |

---

## WS-B — Bootstrap & Migration

| ID | Title | Status | Branch | Report |
|----|-------|--------|--------|--------|
| US-003 | `arch-init` two-phase + CLAUDE.md migration | ✅ | `EPIC-001-US-003-arch-init-claudemd-migration` | [report](.ai/runs/EPIC-001-US-003-arch-init-claudemd-migration/dev/implementation_report.md) |

---

## WS-C — Write Path (self-maintenance)

| ID | Title | Status | Branch | Report |
|----|-------|--------|--------|--------|
| US-004 | Developer `## Architecture Impact` section + `dev-complete` check | ✅ | `EPIC-001-US-004-dev-architecture-impact-section` | [report](.ai/runs/EPIC-001-US-004-dev-architecture-impact-section/dev/implementation_report.md) |
| US-005 | Distill stage: distiller role + subcommands + cap enforcement | ✅ | `EPIC-001-US-005-distill-stage-write-path` | [report](.ai/runs/EPIC-001-US-005-distill-stage-write-path/dev/implementation_report.md) |
| US-006 | ADR lifecycle: epic ADR distill + ticket-land flips | ⬜ | — | — |

---

## WS-D — Drift Detection

| ID | Title | Status | Branch | Report |
|----|-------|--------|--------|--------|
| US-007 | `arch-refresh` drift-check command | ⬜ | — | — |

---

## Progress Summary

- Done: 5 / 7
- In progress: 0 / 7
- Not started: 2 / 7
