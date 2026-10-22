"""/create-ticket command rules and `init --domains`. Run: python3 -m unittest discover -s tests"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / ".ai" / "bin"
sys.path.insert(0, str(BIN))
sys.dont_write_bytecode = True

import ai_run  # noqa: E402
from ai_runner.epic_breakdown_checks import parse_ticket_domains  # noqa: E402

COMMAND = ROOT / ".claude/commands/create-ticket.md"


class CreateTicketRules(unittest.TestCase):
    def setUp(self):
        self.text = COMMAND.read_text()

    def test_run_id_is_file_stem(self):
        self.assertIn("Run id = `<file stem>`", self.text)
        self.assertNotIn("Run id = `<EPIC-dir-name>-<file stem>`", self.text)
        self.assertIn("never calls or depends on `epic-generate-tickets`", self.text)
        self.assertNotIn("Do NOT call `epic-generate-tickets`", self.text)

    def test_ambiguous_stem_and_existing_runs(self):
        self.assertIn("including the same stem under two epics", self.text)
        self.assertIn("run `<id>` already exists; use `/start-ticket <id>`", self.text)
        self.assertIn("If only a run under `<EPIC-dir-name>-<file stem>` exists", self.text)
        self.assertIn("create nothing silently", self.text)

    def test_domain_rules(self):
        for marker in (
            "## Domain (after the source is resolved, before `init`)",
            "operator `--domains a,b` (ordered, first = primary) or single `--domain x` > domain declared in the input > omit",
            "explicit declaration only",
            "Never guess from file paths or prose",
            "matched case-insensitively",
            "Warn about and drop unknown values",
            "Domain problems never block creation",
            "`--domain` differs from the first of `--domains`, ask",
            "`--domain <first> --domains <a,b>`",
        ):
            self.assertIn(marker, self.text, marker)

    def test_usage_and_finish(self):
        self.assertIn("[--domain <name>] [--domains a,b]", self.text)
        self.assertEqual(self.text.count("[--domain <name>] [--domains a,b]"), 2)
        self.assertIn('init <id> "<text>" [--domain <d>] [--domains a,b]', self.text)
        self.assertIn("the applied domain(s)", self.text)
        self.assertIn("Start with: /start-ticket <id>", self.text)

    def test_never_runs_git(self):
        self.assertIn("Never stage, commit, or push with git", self.text)


class ParseTicketDomainsSample(unittest.TestCase):
    def test_sample_bodies(self):
        self.assertEqual(parse_ticket_domains("# T\n\n## Domains\n- `frontend`\n\n## Verification\n- x\n"), ["frontend"])
        self.assertEqual(parse_ticket_domains("## Domains\nbackend, `frontend`\n"), ["backend", "frontend"])
        self.assertEqual(parse_ticket_domains("## Domain\nfrontend\n"), ["frontend"])
        self.assertEqual(parse_ticket_domains("# T\nno domains here\n"), [])


class InitDomainsFlag(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.prev = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(os.chdir, self.prev)
        (self.tmp / ".ai").mkdir()
        cfg = {
            "project_name": "Demo",
            "default_domain": "backend",
            "git": {"base_branch": "main"},
            "domains": {"backend": {"paths": [], "skills": {}}, "frontend": {"paths": [], "skills": {}}},
        }
        (self.tmp / ".ai" / "project_config.json").write_text(json.dumps(cfg))

    def init(self, ticket, *flags):
        argv = sys.argv
        sys.argv = ["ai_run.py", "init", ticket, "req", *flags]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                rc = ai_run.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0)
        return json.loads(ai_run.status_file(ticket).read_text())

    def test_domains_flag_stored(self):
        s = self.init("T-1", "--domain", "backend", "--domains", "backend, frontend,")
        self.assertEqual(s["domain"], "backend")
        self.assertEqual(s["domains"], ["backend", "frontend"])

    def test_without_flag_unchanged(self):
        s = self.init("T-2", "--domain", "frontend")
        self.assertEqual(s["domain"], "frontend")
        self.assertNotIn("domains", s)
        s = self.init("T-3")
        self.assertEqual(s["domain"], "backend")
        self.assertNotIn("domains", s)


if __name__ == "__main__":
    unittest.main()
