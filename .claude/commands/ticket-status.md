---
description: Show a ticket's workflow state and next step (read-only)
argument-hint: <TICKET>
---

Show the status of ticket `$ARGUMENTS`. Read-only: modify nothing.

1. No argument → print usage `/ticket-status <TICKET>` and stop.
2. `python .ai/bin/ai_wrap.py validate-id <TICKET>` must exit 0, else show the error and stop.
3. If `.ai/runs/<TICKET>/status.json` is missing → "Ticket not found. Create it with `/create-ticket`." Stop.
4. Run `python .ai/bin/ai_wrap.py next <TICKET> --json` (if stdout is not valid JSON, retry once with `rtk proxy python .ai/bin/ai_wrap.py next <TICKET> --json`) and read `.ai/runs/<TICKET>/status.json`.
5. Print a compact summary: domain, `current_stage`, `state`, the next step (`kind` + `step`), `fix_round` when set, the last 5 `history` entries (stage, status, note), and the decisions in `architect/architect_review.json`, `review/review_report.json`, `qa/qa_report.json` when those files exist.
6. End with: `Continue with: /start-ticket <TICKET>`.
