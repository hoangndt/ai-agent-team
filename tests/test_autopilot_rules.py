"""/autopilot-ticket command rules (text markers). Run: python3 -m unittest discover -s tests"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import install  # noqa: E402

COMMAND = ROOT / ".claude/commands/autopilot-ticket.md"


class AutopilotRules(unittest.TestCase):
    def setUp(self):
        self.text = COMMAND.read_text()

    def assertMarkers(self, markers):
        for m in markers:
            self.assertIn(m, self.text, m)

    def test_frontmatter(self):
        fm = self.text.split("---", 2)[1]
        self.assertIn("description:", fm)
        self.assertIn("argument-hint: <source> [--domain <name>] [--domains a,b]", fm)
        m = re.search(r"^allowed-tools:\s*(.+)$", fm, re.M)
        self.assertIsNotNone(m)
        tools = {t.strip() for t in m.group(1).split(",")}
        for t in ("Agent", "SendMessage", "Skill", "Bash", "Read", "ToolSearch", "TaskStop", "AskUserQuestion"):
            self.assertIn(t, tools)

    def test_no_permission_bypass_in_claude_files(self):
        for p in (ROOT / ".claude").rglob("*"):
            if p.is_file() and p.name != "settings.local.json":
                self.assertNotIn("bypassPermissions", p.read_text(), str(p))

    def test_installed(self):
        self.assertIn(Path(".claude/commands/autopilot-ticket.md"), install.CLAUDE_MANAGED_FILES)
        self.assertEqual(len(install.CLAUDE_MANAGED_FILES), len(set(install.CLAUDE_MANAGED_FILES)))

    def test_usage_without_arguments(self):
        self.assertMarkers((
            "No arguments → print usage `/autopilot-ticket <source> [--domain <name>] [--domains a,b]` and stop.",
            "Start nothing",
        ))

    def test_reuse_by_loading(self):
        self.assertMarkers((
            "Load `create-ticket` through the Skill tool with args `<source> [--domain <name>] [--domains a,b]`",
            "Load `start-ticket` through the Skill tool with args `<TICKET>` only",
            "never the raw autopilot argument and never `--until`",
            "`$ARGUMENTS` means the args given to that load, not this command's raw argument string",
            "nothing is merged or committed by the orchestrator. That sentence is overridden only after the Confirm step passed",
            "read `.claude/commands/<name>.md` in the project, then `~/.claude/commands/<name>.md`",
            "If neither is found, this is a ping (list item 3).",
        ))

    def test_no_copied_gate_or_loop(self):
        self.assertNotIn("## Report gate (mandatory", self.text)
        self.assertNotIn("## Loop", self.text)
        self.assertMarkers((
            "## Override table",
            "Fix-round cap reached",
            "`*-prepare` exits non-zero",
            "Sub-agent errored, stalled",
            "`*-complete` non-zero or Confirm mismatch",
            "Distill `[BLOCK]`",
            "Report gate PAUSED",
            "Report gate MALFORMED",
            "create-ticket ambiguity, missing MCP, failing MCP",
        ))

    def test_start_ticket_hard_rules_in_force(self):
        self.assertMarkers((
            "the `start-ticket` Hard rules stay fully in force",
            "you NEVER write or edit files under `.ai/runs/` or `.ai/epics/`",
            "you NEVER use `next --run`",
            "your only routing source is `python .ai/bin/ai_wrap.py next <TICKET> --json`",
            "every `*-complete` is confirmed from `status.json`",
        ))

    def test_caffeinate(self):
        self.assertMarkers((
            "`caffeinate -dimsu -t 28800`",
            "`run_in_background`",
            "remember its task id",
            "Release it with TaskStop",
            "kill only the PID this command started, never `pkill`",
            "warn once",
            "release caffeinate (phase 1)",
        ))
        self.assertLess(self.text.index("1. **Caffeinate.**"), self.text.index("2. **Create.**"))

    def test_exhaustive_ping_list(self):
        self.assertIn("This list is exhaustive", self.text)
        section = self.text.split("## When you ping (exhaustive list)")[1].split("\n## ")[0]
        items = re.findall(r"^(\d+)\. ", section, re.M)
        self.assertEqual(items, [str(i) for i in range(1, 11)])
        for marker in (
            "`validate-id` fails at preflight",
            "unresolved or ambiguous",
            "missing or failing",
            "cannot be loaded by the Skill tool nor by file read",
            "A gate item is escalated",
            "failed again after its single retry",
            "content failure (`missing_outputs == []`)",
            "Distill `[BLOCK]` or a second `distill_prepare`",
            "third delegated pause occurs on one stage",
            "already-deferred verification",
            "detached HEAD or missing base branch",
            "a staged-path guard hit",
            "a merge conflict",
            "a hook failure",
            "a failing checkout",
        ):
            self.assertIn(marker, section, marker)

    def test_delegated_gate_policy(self):
        self.assertMarkers((
            "Only the PAUSED branch differs",
            "no `*-complete` before the gate line",
            "An item is **auto-resolved** only if ALL four hold",
            "never invented",
            "It is reversible and local",
            "no production system or production data",
            "no credential or secret handling",
            "does not drop or weaken an acceptance criterion, expand scope beyond the ticket, or choose between product or business alternatives",
            "It is not a verification request",
            "Otherwise the item **escalates**",
            "When in doubt, escalate.",
            "`Operator answered: [delegated to autopilot under standing operator authority]",
            'record them under "## Operator decisions"',
            "rewrite the ENTIRE strict-JSON report from scratch",
            "At most 2 delegated re-dispatches per stage; a third pause on that stage escalates.",
            "`[<step>] autopilot-decision: <item> -> <decision> (<reason>)`",
        ))

    def test_autopilot_log(self):
        self.assertMarkers((
            "`${TMPDIR:-/tmp}/autopilot-<runid>.md`",
            "outside the repo working tree and outside `.ai/runs`/`.ai/epics`",
            "The session scratchpad is deliberately NOT used",
            "Append-only (`>>`)",
            "Re-read the file (do not recall it from memory) at Finalize",
            "a pre-existing file at that path is stale",
            "is removed before the first append",
            "remove the file after Finalize step 7 verification passes",
            "leave it in place for the resume",
            "Autopilot log not found on resume; delegated decisions/deferrals from earlier sessions may be missing",
        ))

    def test_resume_for_non_local_sources(self):
        self.assertMarkers((
            'any `create-ticket` outcome of "run `<id>` already exists" is also a resume with that id',
            'its "use existing / new ID" question and its "older `<EPIC>-<stem>` run" question are both answered "use existing"',
            "A second run is never created.",
        ))

    def test_operator_verification(self):
        self.assertMarkers((
            "ToolSearch for MCP tools by keyword (`playwright`, `browser`, `chrome`, `puppeteer`)",
            "Do not assume tool names.",
            "`curl`",
            "non-destructive",
            "`Operator answered: [verified by autopilot via <tool>]",
            "never report a pass that was not observed",
            "`localhost`, `127.0.0.1` or `::1`",
            "explicitly name as dev/stage",
            "Any other or ambiguous host",
            "`Operator answered: [not verifiable by autopilot; deferred to operator] treat as UNVERIFIED",
            "**Deferred verifications**",
            "automation suggestion",
            "Playwright MCP server",
            "not executed",
            "A deferral is never repeated in a loop.",
            "Never put credentials, tokens, cookies or secrets in any `Operator answered:` text, the Autopilot log or a commit body",
        ))

    def test_finalize(self):
        self.assertMarkers((
            "Runs only after `start-ticket` reached `kind == done` and Confirm passed",
            "`git add -A`",
            "`git reset -q -- .ai/runs`",
            "`git diff --cached --name-only`",
            "ping instead of committing",
            "`.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `credentials*`, `secrets*`, `*.keystore`",
            "The guard also runs before the squash commit",
            "subject `feat(<TICKET>): <one-line summary>`",
            "Decision log and Deferred verifications",
            "`git checkout <base>`",
            "`git merge --squash <branch>`",
            "The feature branch is kept.",
            "the step 4 commit is the final state; nothing to merge",
            "re-derive the state from `git branch --show-current` and `git status --porcelain`",
            "`git rev-list <base>..<branch>` is empty",
            "skip the squash commit when nothing is staged after the squash",
            "`git reset --merge`",
            "applies only on the squash path, after `git merge --squash` has started",
            "Never run it at step 1",
            "rename or unstage the file",
            "`prompt_path` null where a dispatch is required",
            "then `git checkout <branch>`",
            "Never bypass hooks",
            "needs no checkout",
            "excluding `.ai/runs/`",
            "`git log -1 --oneline`",
            "listed by path in the final summary",
        ))

    def test_forbidden_commands(self):
        hard = self.text.split("## Hard rules")[1].split("\n## ")[0]
        for marker in (
            "Never `git push`",
            "`--force`",
            "`--no-verify`",
            "`reset --hard`",
            "never delete a branch",
            "never `pkill`",
        ):
            self.assertIn(marker, hard, marker)

    def test_no_whole_dir_or_settings_edits(self):
        self.assertNotIn("settings.local.json", self.text)


if __name__ == "__main__":
    unittest.main()
