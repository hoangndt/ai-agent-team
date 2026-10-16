import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.py"
sys.path.insert(0, str(ROOT))
import install  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, str(INSTALL), *args], capture_output=True, text=True, input="n\n")


class ClaudeInstallTests(unittest.TestCase):
    def test_project_install_copies_managed_files_only(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            (t / ".claude" / "commands").mkdir(parents=True)
            (t / ".claude" / "commands" / "mine.md").write_text("keep")
            (t / ".claude" / "settings.local.json").write_text("{}")
            r = run("--target", d, "--yes")
            self.assertEqual(r.returncode, 0, r.stderr)
            for rel in install.CLAUDE_MANAGED_FILES:
                self.assertTrue((t / rel).is_file(), rel)
            self.assertEqual((t / ".claude/commands/mine.md").read_text(), "keep")
            self.assertEqual((t / ".claude/settings.local.json").read_text(), "{}")

    def test_backup_preserves_overwritten_file(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            f = t / ".claude/commands/start-ticket.md"
            f.parent.mkdir(parents=True)
            f.write_text("old")
            r = run("--target", d, "--yes", "--backup")
            self.assertEqual(r.returncode, 0, r.stderr)
            backups = [p for p in t.rglob("start-ticket.md") if p.read_text() == "old"]
            self.assertEqual(len(backups), 1)
            self.assertNotEqual(f.read_text(), "old")

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as h:
            r = run("--target", d, "--dry-run", "--global-claude", "--claude-home", h)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(list(Path(d).iterdir()), [])
            self.assertEqual(list(Path(h).iterdir()), [])

    def test_global_claude_writes_home_and_skips_project_claude(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as h:
            (Path(h) / "commands").mkdir()
            (Path(h) / "commands" / "mine.md").write_text("keep")
            r = run("--target", d, "--yes", "--global-claude", "--claude-home", h)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((Path(h) / "commands" / "start-ticket.md").is_file())
            self.assertTrue((Path(h) / "agents" / "workflow-step.md").is_file())
            self.assertEqual((Path(h) / "commands" / "mine.md").read_text(), "keep")
            self.assertFalse((Path(d) / ".claude").exists())

    def test_declined_project_confirm_leaves_global_untouched(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as h:
            r = run("--target", d, "--global-claude", "--claude-home", h)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(list(Path(h).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
