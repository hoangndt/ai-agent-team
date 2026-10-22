"""Argument parsing and the main entry point."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .constants import EPICS, KNOWN_SUBCOMMANDS, RUNS
from .state import init_ticket, resolve_engine
from .architect_stages import (
    architect_complete, architect_fix_complete, architect_fix_prepare,
    architect_prepare, architect_review_complete, architect_review_prepare,
)
from .dev_qa_stages import (
    dev_complete, dev_fix_complete, dev_fix_prepare, dev_prepare, qa_complete,
    qa_prepare, review_complete, review_prepare,
)
from .distill_stages import distill_complete, distill_prepare
from .arch_stages import (
    arch_init_complete, arch_init_prepare, arch_refresh_complete, arch_refresh_prepare,
)
from .epic_stages import (
    adr_distill_complete, adr_distill_prepare, epic_analysis_complete,
    epic_analysis_prepare, epic_breakdown_complete, epic_breakdown_prepare,
    epic_design_complete, epic_design_fix_complete, epic_design_fix_prepare,
    epic_design_prepare, epic_generate_tickets, epic_init, epic_review_complete,
    epic_review_prepare,
)
from .epic_review_stages import (
    epic_analysis_fix_complete, epic_analysis_fix_prepare,
    epic_analysis_review_complete, epic_analysis_review_prepare,
    epic_breakdown_fix_complete, epic_breakdown_fix_prepare,
    epic_breakdown_review_complete, epic_breakdown_review_prepare,
)
from .routing import epic_next_step, next_step, show_epic_status, show_status
from .autoflow import run_epic_autoflow, run_ticket_autoflow


def maybe_init_and_run(
    id: str,
    kind: str,
    run_dir: Path,
    inline_req: Optional[str],
    no_prompt: bool,
    run_auto: bool,
    init_fn,
    next_fn,
    init_kwargs: dict,
    engine: str = "claude",
) -> None:
    if not run_dir.exists():
        if no_prompt and not inline_req:
            print(
                "Error: --no-prompt requires an inline requirement argument when the directory does not exist.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not no_prompt:
            try:
                answer = input(f"{kind} not found. Initialize new {kind.lower()}? [Y/n]").strip().lower()
            except EOFError:
                print(
                    "[ERROR] No input available. Use --no-prompt with an inline requirement.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if answer == "n":
                print("[ABORTED]")
                return
        if inline_req:
            requirement = inline_req
        else:
            try:
                requirement = input("Enter requirement: ").strip()
            except EOFError:
                print(
                    "[ERROR] No input available. Use --no-prompt with an inline requirement.",
                    file=sys.stderr,
                )
                sys.exit(1)
        init_fn(id, requirement, **init_kwargs)
        print(f"[OK] Initialized {id}. Run 'next {id} --run' when ready.")
        return
    next_fn(id, execute=True, run_auto=run_auto, engine=engine)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reusable file-referenced prepare/complete workflow for local AI agent team."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a ticket run.")
    p_init.add_argument("ticket", help="Ticket ID, e.g. TICKET-123")
    p_init.add_argument("requirement", help="Initial input text")
    p_init.add_argument(
        "--domain",
        default="",
        help="Optional domain override, e.g. backend or frontend",
    )
    p_init.add_argument(
        "--domains",
        default="",
        help="Optional comma-separated domains, e.g. backend,frontend (first = primary).",
    )

    for cmd in [
        "architect-prepare",
        "architect-complete",
        "architect-review-prepare",
        "architect-review-complete",
        "architect-fix-prepare",
        "architect-fix-complete",
        "dev-prepare",
        "dev-fix-prepare",
        "dev-fix-complete",
        "dev-complete",
        "review-prepare",
        "review-complete",
        "qa-prepare",
        "qa-complete",
        "distill-prepare",
        "distill-complete",
        "status",
    ]:
        p = sub.add_parser(cmd, help=f"Run {cmd}")
        p.add_argument("ticket", help="Ticket ID, e.g. TICKET-123")

    sub.add_parser(
        "arch-init-prepare",
        help="Project-level: bootstrap project_config.json domains (if missing) and generate "
        "the arch-init prompt to seed the architecture vault. Takes no ticket id.",
    )
    sub.add_parser(
        "arch-init-complete",
        help="Verify arch-init outputs (vault files + CLAUDE.md import line). Takes no ticket id.",
    )

    sub.add_parser(
        "arch-refresh-prepare",
        help="Project-level: generate the arch-refresh prompt to re-derive system-overview.md "
        "from the code and diff it for drift. Takes no ticket id.",
    )
    sub.add_parser(
        "arch-refresh-complete",
        help="Verify the drift report was written and system-overview.md is unchanged. "
        "Takes no ticket id.",
    )

    p_next = sub.add_parser("next", help="Show or run the next step.")
    p_next.add_argument("ticket", help="Ticket ID, e.g. TICKET-123")
    p_next.add_argument(
        "--run",
        action="store_true",
        help="Execute the next step instead of only printing it.",
    )
    p_next.add_argument(
        "--run-auto",
        action="store_true",
        help="Execute the next step and automatically open Claude in a new WezTerm tab with the prompt pre-loaded.",
    )
    p_next.add_argument(
        "--engine",
        default=None,
        help="AI engine to use for WezTerm spawning (e.g. claude, codex). Overrides engine.default in project_config.json.",
    )

    # ── Epic subcommands ──────────────────────────────────────────────────────
    p_epic_init = sub.add_parser("epic-init", help="Initialize an epic run.")
    p_epic_init.add_argument("epic", help="Epic ID, e.g. EPIC-001")
    p_epic_init.add_argument("requirement", help="Initial epic requirement text")
    p_epic_init.add_argument(
        "--domains",
        default="",
        metavar="DOMAINS",
        help="Comma-separated domains, e.g. backend,frontend. Defaults to all domains in config.",
    )
    p_epic_init.add_argument(
        "--domain",
        default="",
        metavar="DOMAIN",
        help="[DEPRECATED] Use --domains instead. Kept for backward compatibility.",
    )

    for cmd in [
        "epic-analysis-prepare",
        "epic-analysis-complete",
        "epic-design-prepare",
        "epic-design-complete",
        "epic-review-prepare",
        "epic-review-complete",
        "epic-design-fix-prepare",
        "epic-design-fix-complete",
        "epic-breakdown-prepare",
        "epic-breakdown-complete",
        "epic-analysis-review-prepare",
        "epic-analysis-review-complete",
        "epic-analysis-fix-prepare",
        "epic-analysis-fix-complete",
        "epic-breakdown-review-prepare",
        "epic-breakdown-review-complete",
        "epic-breakdown-fix-prepare",
        "epic-breakdown-fix-complete",
        "adr-distill-prepare",
        "adr-distill-complete",
        "epic-status",
    ]:
        p = sub.add_parser(cmd, help=f"Run {cmd}")
        p.add_argument("epic", help="Epic ID, e.g. EPIC-001")

    p_gen = sub.add_parser("epic-generate-tickets", help="Scaffold input.md for each epic breakdown ticket.")
    p_gen.add_argument("epic", help="Epic ID, e.g. EPIC-001")
    p_gen.add_argument("--init-dirs", action="store_true", help="Also create full run directory structure for each ticket.")

    p_epic_next = sub.add_parser("epic-next", help="Show or run the next epic step.")
    p_epic_next.add_argument("epic", help="Epic ID, e.g. EPIC-001")
    p_epic_next.add_argument(
        "--run",
        action="store_true",
        help="Execute the next epic step instead of only printing it.",
    )
    p_epic_next.add_argument(
        "--run-auto",
        action="store_true",
        help="Execute the next epic step and automatically open Claude in a new WezTerm tab.",
    )
    p_epic_next.add_argument(
        "--engine",
        default=None,
        help="AI engine to use for WezTerm spawning (e.g. claude, codex). Overrides engine.default in project_config.json.",
    )

    # ── Shortcut subcommands ──────────────────────────────────────────────────
    p_ticket = sub.add_parser("ticket", help="Run ticket workflow shortcuts.")
    p_ticket.add_argument("ticket_id", help="Ticket ID, e.g. TICKET-123")
    p_ticket.add_argument(
        "requirement",
        nargs="?",
        default=None,
        help="Inline requirement (used during initialization; ignored if directory exists)",
    )
    p_ticket.add_argument("--next", action="store_true", help="Advance to the next step only.")
    p_ticket.add_argument(
        "--auto",
        action="store_true",
        help="Automatically open Claude in a new WezTerm tab with the prompt pre-loaded.",
    )
    p_ticket.add_argument(
        "--auto-flow",
        action="store_true",
        help="Run the full ticket workflow automatically: spawn Claude, wait for completion, advance through all steps until done.",
    )
    p_ticket.add_argument("--no-prompt", action="store_true", help="Skip confirmation prompts.")
    p_ticket.add_argument("--domain", default="", help="Domain override, e.g. backend or frontend.")
    p_ticket.add_argument(
        "--engine",
        default=None,
        help="AI engine to use for WezTerm spawning (e.g. claude, codex). Overrides engine.default in project_config.json.",
    )

    p_epic_shortcut = sub.add_parser("epic", help="Run epic workflow shortcuts.")
    p_epic_shortcut.add_argument("epic_id", help="Epic ID, e.g. EPIC-001")
    p_epic_shortcut.add_argument(
        "requirement",
        nargs="?",
        default=None,
        help="Inline requirement (used during initialization; ignored if directory exists)",
    )
    p_epic_shortcut.add_argument("--next", action="store_true", help="Advance to the next step only.")
    p_epic_shortcut.add_argument(
        "--auto",
        action="store_true",
        help="Automatically open Claude in a new WezTerm tab with the prompt pre-loaded.",
    )
    p_epic_shortcut.add_argument(
        "--auto-flow",
        action="store_true",
        help="Run the full epic workflow automatically: spawn Claude, wait for completion, advance through all steps until done.",
    )
    p_epic_shortcut.add_argument("--no-prompt", action="store_true", help="Skip confirmation prompts.")
    p_epic_shortcut.add_argument(
        "--domains",
        default="",
        metavar="DOMAINS",
        help="Comma-separated domains, e.g. backend,frontend.",
    )
    p_epic_shortcut.add_argument(
        "--engine",
        default=None,
        help="AI engine to use for WezTerm spawning (e.g. claude, codex). Overrides engine.default in project_config.json.",
    )

    return parser


def main() -> int:
    # Positional shortcut: ai_run.py <TICKET> [inline_req]
    _positional = (
        len(sys.argv) >= 2
        and not sys.argv[1].startswith("-")
        and sys.argv[1] not in KNOWN_SUBCOMMANDS
    )
    if not _positional:
        parser = build_parser()
        args = parser.parse_args()

    try:
        if _positional:
            ticket_id = sys.argv[1]
            inline_req = sys.argv[2] if len(sys.argv) > 2 else None
            if inline_req and inline_req.startswith("-"):
                print(
                    f"[ERROR] Flags are not supported in positional mode. "
                    f"Use 'ai_run.py ticket {ticket_id} ...' for flag support.",
                    file=sys.stderr,
                )
                return 1
            maybe_init_and_run(
                id=ticket_id,
                kind="Ticket",
                run_dir=RUNS / ticket_id,
                inline_req=inline_req,
                no_prompt=False,
                run_auto=False,
                init_fn=init_ticket,
                next_fn=next_step,
                init_kwargs={},
            )
        elif args.command == "init":
            init_domains = [d.strip() for d in args.domains.split(",") if d.strip()]
            init_ticket(
                args.ticket,
                args.requirement,
                domain=args.domain,
                domains=init_domains or None,
            )
        elif args.command == "architect-prepare":
            architect_prepare(args.ticket)
        elif args.command == "architect-complete":
            architect_complete(args.ticket)
        elif args.command == "architect-review-prepare":
            architect_review_prepare(args.ticket)
        elif args.command == "architect-review-complete":
            architect_review_complete(args.ticket)
        elif args.command == "architect-fix-prepare":
            architect_fix_prepare(args.ticket)
        elif args.command == "architect-fix-complete":
            architect_fix_complete(args.ticket)
        elif args.command == "dev-prepare":
            dev_prepare(args.ticket)
        elif args.command == "dev-fix-prepare":
            dev_fix_prepare(args.ticket)
        elif args.command == "dev-fix-complete":
            dev_fix_complete(args.ticket)
        elif args.command == "dev-complete":
            dev_complete(args.ticket)
        elif args.command == "review-prepare":
            review_prepare(args.ticket)
        elif args.command == "review-complete":
            review_complete(args.ticket)
        elif args.command == "qa-prepare":
            qa_prepare(args.ticket)
        elif args.command == "qa-complete":
            qa_complete(args.ticket)
        elif args.command == "distill-prepare":
            distill_prepare(args.ticket)
        elif args.command == "distill-complete":
            distill_complete(args.ticket)
        elif args.command == "status":
            show_status(args.ticket)
        elif args.command == "arch-init-prepare":
            arch_init_prepare()
        elif args.command == "arch-init-complete":
            arch_init_complete()
        elif args.command == "arch-refresh-prepare":
            arch_refresh_prepare()
        elif args.command == "arch-refresh-complete":
            arch_refresh_complete()
        elif args.command == "next":
            engine = resolve_engine(args.engine)
            next_step(args.ticket, execute=args.run, run_auto=args.run_auto, engine=engine)
        elif args.command == "epic-init":
            domains_arg = args.domains
            if not domains_arg and getattr(args, "domain", ""):
                print(
                    "[DEPRECATED] --domain is deprecated for epic-init; use --domains instead."
                )
                domains_arg = args.domain
            epic_init(args.epic, args.requirement, domains=domains_arg)
        elif args.command == "epic-analysis-prepare":
            epic_analysis_prepare(args.epic)
        elif args.command == "epic-analysis-complete":
            epic_analysis_complete(args.epic)
        elif args.command == "epic-design-prepare":
            epic_design_prepare(args.epic)
        elif args.command == "epic-design-complete":
            epic_design_complete(args.epic)
        elif args.command == "epic-review-prepare":
            epic_review_prepare(args.epic)
        elif args.command == "epic-review-complete":
            epic_review_complete(args.epic)
        elif args.command == "epic-design-fix-prepare":
            epic_design_fix_prepare(args.epic)
        elif args.command == "epic-design-fix-complete":
            epic_design_fix_complete(args.epic)
        elif args.command == "epic-breakdown-prepare":
            epic_breakdown_prepare(args.epic)
        elif args.command == "epic-breakdown-complete":
            epic_breakdown_complete(args.epic)
        elif args.command == "epic-analysis-review-prepare":
            epic_analysis_review_prepare(args.epic)
        elif args.command == "epic-analysis-review-complete":
            epic_analysis_review_complete(args.epic)
        elif args.command == "epic-analysis-fix-prepare":
            epic_analysis_fix_prepare(args.epic)
        elif args.command == "epic-analysis-fix-complete":
            epic_analysis_fix_complete(args.epic)
        elif args.command == "epic-breakdown-review-prepare":
            epic_breakdown_review_prepare(args.epic)
        elif args.command == "epic-breakdown-review-complete":
            epic_breakdown_review_complete(args.epic)
        elif args.command == "epic-breakdown-fix-prepare":
            epic_breakdown_fix_prepare(args.epic)
        elif args.command == "epic-breakdown-fix-complete":
            epic_breakdown_fix_complete(args.epic)
        elif args.command == "adr-distill-prepare":
            adr_distill_prepare(args.epic)
        elif args.command == "adr-distill-complete":
            adr_distill_complete(args.epic)
        elif args.command == "epic-generate-tickets":
            epic_generate_tickets(args.epic, init_dirs=args.init_dirs)
        elif args.command == "epic-status":
            show_epic_status(args.epic)
        elif args.command == "epic-next":
            engine = resolve_engine(args.engine)
            epic_next_step(args.epic, execute=args.run, run_auto=args.run_auto, engine=engine)
        elif args.command == "ticket":
            engine = resolve_engine(args.engine)
            if getattr(args, "auto_flow", False):
                run_ticket_autoflow(args.ticket_id, engine=engine)
            elif args.next:
                next_step(args.ticket_id, execute=True, run_auto=args.auto, engine=engine)
            else:
                maybe_init_and_run(
                    id=args.ticket_id,
                    kind="Ticket",
                    run_dir=RUNS / args.ticket_id,
                    inline_req=args.requirement,
                    no_prompt=args.no_prompt,
                    run_auto=args.auto,
                    init_fn=init_ticket,
                    next_fn=next_step,
                    init_kwargs={"domain": args.domain},
                    engine=engine,
                )
        elif args.command == "epic":
            engine = resolve_engine(args.engine)
            if getattr(args, "auto_flow", False):
                run_epic_autoflow(args.epic_id, engine=engine)
            elif args.next:
                epic_next_step(args.epic_id, execute=True, run_auto=args.auto, engine=engine)
            else:
                maybe_init_and_run(
                    id=args.epic_id,
                    kind="Epic",
                    run_dir=EPICS / args.epic_id,
                    inline_req=args.requirement,
                    no_prompt=args.no_prompt,
                    run_auto=args.auto,
                    init_fn=epic_init,
                    next_fn=epic_next_step,
                    init_kwargs={"domains": args.domains},
                    engine=engine,
                )
        else:
            parser.print_help()
            return 2
    except KeyboardInterrupt:
        print("\n[ABORTED]")
        return 130
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0
