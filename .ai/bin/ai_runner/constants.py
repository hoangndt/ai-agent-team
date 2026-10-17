"""Static constants and sentinel helpers shared by every runner module."""

import re
from pathlib import Path
from typing import Dict


BASE = Path(".ai")


RUNS = BASE / "runs"


AGENTS = BASE / "agents"


def make_sentinel(run_id: str) -> str:
    return f"[AGENT_COMPLETE:{run_id}]"


def make_sentinel_instruction(run_id: str) -> str:
    sentinel = make_sentinel(run_id)
    return (
        "---\n"
        "IMPORTANT: After you have finished writing all required output files, "
        "print exactly the following on its own line and nothing else after it:\n"
        + sentinel
    )


FIGMA_URL_RE = re.compile(
    r"https?://(?:www\.)?figma\.com/(?:file|design|proto)/[^\s)>\\\]]+",
    re.IGNORECASE,
)


ENGINE_REGISTRY: Dict[str, Dict] = {
    "claude": {
        "base": ["claude", "--dangerously-skip-permissions"],
        "supports_model_effort": True,
    },
    "codex": {
        "base": ["codex", "--dangerously-bypass-approvals-and-sandbox"],
        "supports_model_effort": False,
    },
}


KNOWN_SUBCOMMANDS = frozenset({
    "init", "next", "status",
    "architect-prepare", "architect-complete",
    "architect-review-prepare", "architect-review-complete",
    "architect-fix-prepare", "architect-fix-complete",
    "dev-prepare", "dev-complete", "dev-fix-prepare", "dev-fix-complete",
    "review-prepare", "review-complete",
    "qa-prepare", "qa-complete",
    "distill-prepare", "distill-complete",
    "epic-init", "epic-next", "epic-status",
    "epic-analysis-prepare", "epic-analysis-complete",
    "epic-design-prepare", "epic-design-complete",
    "epic-review-prepare", "epic-review-complete",
    "epic-design-fix-prepare", "epic-design-fix-complete",
    "epic-breakdown-prepare", "epic-breakdown-complete",
    "adr-distill-prepare", "adr-distill-complete",
    "epic-generate-tickets",
    "ticket", "epic",
    "arch-init-prepare", "arch-init-complete",
    "arch-refresh-prepare", "arch-refresh-complete",
})


# Every *-prepare step; must equal the keys of the routing prepare->complete
# tables (enforced by a unit test, since constants cannot import routing).
KNOWN_PREPARE_STEPS = frozenset({
    "architect-prepare", "architect-review-prepare", "architect-fix-prepare",
    "dev-prepare", "dev-fix-prepare", "review-prepare", "qa-prepare", "distill-prepare",
    "epic-analysis-prepare", "epic-design-prepare", "epic-design-fix-prepare",
    "epic-review-prepare", "epic-breakdown-prepare", "adr-distill-prepare",
})

# Sentinel ticket id reused for arch-init's per-run status/prompt machinery.
# arch-init has no CLI ticket argument, but every reused helper (update_stage,
# complete_stage, fail_stage, ensure_non_empty_files, build_project_context,
# get_effective_role_skills) requires a ticket id to key a status.json, so a
# fixed sentinel id is used instead of forking ticket-less variants of them.
ARCH_INIT_TICKET = "_arch-init"


# Separate sentinel for arch-refresh, so the two ticket-less operator
# commands never share/clobber the same status.json.
ARCH_REFRESH_TICKET = "_arch-refresh"


# ── EPIC PATH HELPERS ──────────────────────────────────────────────────────────

EPICS = BASE / "epics"
