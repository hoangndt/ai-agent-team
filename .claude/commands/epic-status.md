---
description: Show an epic's workflow state and next step (read-only)
argument-hint: <EPIC>
---

Show the status of epic `$ARGUMENTS`. Read-only: modify nothing.

1. No argument → print usage `/epic-status <EPIC>` and stop.
2. `python .ai/bin/ai_wrap.py validate-id <EPIC>` must exit 0, else show the error and stop.
3. If `.ai/epics/<EPIC>/status.json` is missing → "Epic not found. Create it with `/create-epic`." Stop.
4. Run `python .ai/bin/ai_wrap.py epic-next <EPIC> --json` (if stdout is not valid JSON, retry once with `rtk proxy python .ai/bin/ai_wrap.py epic-next <EPIC> --json`) and read `.ai/epics/<EPIC>/status.json`.
5. Print a compact summary: domains, `current_stage`, `state`, the next step (`kind` + `step`), `fix_round` when set, the last 5 `history` entries (stage, status, note), the decision in `review/epic_review.json` when it exists, and the number of ticket files under `breakdown/tickets/`.
6. End with: `Continue with: /start-epic <EPIC>`.
