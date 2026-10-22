import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMANDS = [ROOT / ".claude/commands/start-ticket.md", ROOT / ".claude/commands/start-epic.md"]
AGENTS = [
    ROOT / ".claude/agents/workflow-step.md",
    ROOT / ".claude/agents/workflow-step-medium.md",
    ROOT / ".claude/agents/workflow-step-high.md",
]
LABELS = ("QUESTIONS", "ASSUMPTIONS", "BLOCKERS")
DISPATCH_SHAPE = (
    "Final message: the 4 labelled sections FILES WRITTEN, QUESTIONS, ASSUMPTIONS, "
    "BLOCKERS, with the literal word none when a section is empty."
)


def normalize(span):
    s = span.strip()
    s = re.sub(r"^-\s+", "", s)
    s = re.sub(r"[*_`]", "", s).strip()
    s = s.rstrip(".").strip()
    return s.lower()


def classify(message):
    """Return 'malformed', 'clear' or 'paused' for a full sub-agent final message."""
    labels = ("FILES WRITTEN",) + LABELS
    positions = {}
    for label in labels:
        m = re.search(rf"^{label}:", message, re.M)
        if not m:
            return "malformed"
        positions[label] = m
    spans = {}
    for label in LABELS:
        start = positions[label].end()
        later = [m.start() for lab, m in positions.items() if m.start() > positions[label].start()]
        end = min(later) if later else len(message)
        spans[label] = message[start:end]
    if any(not v.strip() for v in spans.values()):
        return "malformed"
    if all(normalize(v) == "none" for v in spans.values()):
        return "clear"
    return "paused"


def report(q="none", a="none", b="none"):
    return f"FILES WRITTEN: x\nQUESTIONS: {q}\nASSUMPTIONS: {a}\nBLOCKERS: {b}"


def body(path):
    text = path.read_text()
    return text.split("---", 2)[2]


class ClassifierTable(unittest.TestCase):
    def test_clear(self):
        for v in ("none", "None.", "NONE", "- none", "**none**", "`none`"):
            self.assertEqual(classify(report(b=v)), "clear", v)

    def test_paused(self):
        cases = [
            report(b="none, but tests could not run"),
            report(b="\n- cannot run pytest"),
            report(b="- cannot run pytest (not installed)"),
            report(b="none\n- tests failed"),
            report(b="n/a"),
            report(q="- which branch?"),
            report(a="- treated X as Y"),
        ]
        for c in cases:
            self.assertEqual(classify(c), "paused", c)

    def test_malformed(self):
        self.assertEqual(classify("FILES WRITTEN: x\nQUESTIONS: none\nASSUMPTIONS: none\nBLOCKERS:"), "malformed")
        self.assertEqual(classify("FILES WRITTEN: x\nQUESTIONS: none\nBLOCKERS: none"), "malformed")
        self.assertEqual(classify("All done, nothing to report."), "malformed")


class CommandRules(unittest.TestCase):
    def test_report_gate_present(self):
        for p in COMMANDS:
            t = p.read_text()
            with self.subTest(p.name):
                self.assertIn("## Report gate (mandatory", t)
                for label in LABELS:
                    self.assertIn(label, t)
                for marker in (
                    "to the next label or the end of the message, including continuation lines",
                    "equals `none`",
                    "Fail closed",
                    "gate: MALFORMED",
                    "gate: PAUSED (Q=<n> A=<n> B=<n>)",
                    "gate: clear",
                    "protocol violation",
                    "\"answer\"",
                    "\"accept and continue\"",
                    "\"abort\"",
                    "never decide an item is non-blocking",
                    "You never waive, downgrade or skip a QUESTIONS/ASSUMPTIONS/BLOCKERS item",
                    "fix-round dispatch (new agent or SendMessage)",
                    "re-dispatch",
                    "Operator answered:",
                ):
                    self.assertIn(marker, t, marker)

    def test_recommended_answers(self):
        for p in COMMANDS:
            t = p.read_text()
            with self.subTest(p.name):
                for marker in (
                    "`Recommended: <concrete answer or decision>`",
                    "orchestrator recommendation, not yet an answer",
                    "\"use recommended\" / \"edit\"",
                    "\"write my own\"",
                    "Never send a recommendation without that explicit choice",
                    "never read whole prompt/report files and never write under `.ai/runs/` or `.ai/epics/`",
                    "never invent one",
                ):
                    self.assertIn(marker, t, marker)

    def test_recommendation_text_shared(self):
        def segment(p):
            t = p.read_text()
            i = t.index("Do not start from a blank prompt")
            return t[i:t.index("ALWAYS re-dispatch the same stage", i)]

        self.assertEqual(segment(COMMANDS[0]), segment(COMMANDS[1]))

    def test_removed_wording(self):
        for p in COMMANDS:
            t = p.read_text()
            self.assertNotIn("ASSUMPTIONS alone do not pause", t)
            self.assertNotIn("list them in your stage summary", t)
            self.assertNotIn("(or none)", t)

    def test_dispatch_shape_identical(self):
        for p in COMMANDS:
            self.assertIn(DISPATCH_SHAPE, p.read_text(), p.name)

    def test_loop_references_gate(self):
        for p in COMMANDS:
            t = p.read_text()
            self.assertGreaterEqual(t.count("Report gate (mandatory, below)"), 2, p.name)

    def test_resume_4a_unconditional(self):
        for p in COMMANDS:
            t = p.read_text()
            self.assertIn("ALWAYS dispatch with the resume addendum", t, p.name)
            self.assertIn("even if `missing_outputs == []`", t, p.name)

    def test_distill_retry_gated_in_ticket(self):
        t = COMMANDS[0].read_text()
        self.assertIn("pass the Report gate, then run", t)
        self.assertIn("distill re-dispatch", t)


class AgentRules(unittest.TestCase):
    def test_bodies_identical(self):
        bodies = {body(p) for p in AGENTS}
        self.assertEqual(len(bodies), 1)

    def test_contract_clauses(self):
        t = body(AGENTS[0])
        for marker in (
            "`QUESTIONS`:",
            "`ASSUMPTIONS`:",
            "`BLOCKERS`:",
            "single literal word `none`",
            "A bare label with nothing after it is malformed",
            "`- ` bullet items",
            "must not live only in prose or in a report file",
            "list only NEW items",
            "no text after them",
            "material choices",
        ):
            self.assertIn(marker, t, marker)


if __name__ == "__main__":
    unittest.main()
