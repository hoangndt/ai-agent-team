"""Prompt contracts for the scope-minimality rules in the role files under .ai/agents.

The tests read the role files from disk and, for the fix-round precedence text, assemble
real fix prompts. They prove the text exists and reaches the prompts; they cannot prove a
model obeys it.

Run: python3 -m unittest discover -s tests
"""
import json
import re
import unittest
from pathlib import Path

import test_epic_review_flow as base

ROOT = base.ROOT
AGENTS = ROOT / ".ai" / "agents"
ai_run = base.ai_run
quiet = base.quiet
EPIC = base.EPIC

MARKERS = {
    "epic_analyst": ["MVP SCOPE DISCIPLINE"],
    "epic_analysis_reviewer": ["ANALYSIS REVIEW MATERIALITY"],
    "epic_designer": ["MINIMUM VIABLE ARCHITECTURE", "ARCHITECTURAL DECISION SIGNIFICANCE"],
    "epic_reviewer": ["DESIGN REVIEW MATERIALITY"],
    "epic_planner": ["OUTCOME-FIRST STORY BREAKDOWN", "BACKLOG REDUCTION PASS",
                     "DEPENDENCY DISCIPLINE", "SCOPE PRESERVATION"],
    "epic_breakdown_reviewer": ["NECESSITY-FIRST BREAKDOWN REVIEW"],
    "architect": ["ASSUMPTION DISCIPLINE"],
    "architect_reviewer": ["TICKET DESIGN REVIEW SCOPE"],
    "developer": ["IMPLEMENTATION MINIMALITY"],
    "distiller": ["ADR NECESSITY RULE"],
}
UNCHANGED_ROLES = ("arch_init", "reviewer", "qa")
REVIEWERS = ("epic_analysis_reviewer", "epic_reviewer", "epic_breakdown_reviewer", "architect_reviewer")
PRODUCERS = ("epic_analyst", "epic_designer", "epic_planner", "architect")
JSON_REVIEWERS = REVIEWERS
FIVE_POINT = ("the requirement or invariant it protects", "the concrete failure scenario",
              "the impact if omitted", "the simplest acceptable mitigation",
              "why documenting the limitation or deferring is insufficient")


def role(name):
    return (AGENTS / f"{name}.md").read_text()


class MarkerTests(unittest.TestCase):
    def test_markers_present(self):
        for name, markers in MARKERS.items():
            text = role(name)
            for marker in markers:
                self.assertIn(marker, text, f"{name}: {marker}")

    def test_unchanged_roles_have_no_markers(self):
        every = [m for markers in MARKERS.values() for m in markers]
        for name in UNCHANGED_ROLES:
            text = role(name)
            for marker in every:
                self.assertNotIn(marker, text, f"{name}: {marker}")

    def test_safety_clause_in_edited_roles(self):
        for name in MARKERS:
            if name == "distiller":
                continue
            self.assertIn("mandatory security, financial", role(name).lower(), name)

    def test_no_numeric_sizing(self):
        for name in MARKERS:
            for rx in base.SIZING_NUMBER_RES:
                self.assertIsNone(rx.search(role(name)), f"{name}: {rx.pattern}")

    def test_no_count_or_length_caps(self):
        for name in MARKERS:
            low = role(name).lower()
            for phrase in ("ticket count of", "maximum number of tickets", "at most", "no more than",
                           "fewer tickets"):
                self.assertNotIn(phrase, low, f"{name}: {phrase}")


class ReviewerContractTests(unittest.TestCase):
    def test_json_contract_kept(self):
        for name in JSON_REVIEWERS:
            text = role(name)
            self.assertIn("approve|request_changes|block", text, name)
            self.assertIn("high|medium|low", text, name)
            for key in ("decision", "issues", "severity", "area", "message", "summary"):
                self.assertIn(f'"{key}"', text, f"{name}: {key}")

    def test_approve_only_without_high(self):
        for name in ("epic_analysis_reviewer", "epic_breakdown_reviewer"):
            self.assertIn("Use `approve` only when there are no high severity issues", role(name), name)
            self.assertTrue(role(name).startswith("You are Epic"), name)

    def test_breakdown_area_list_is_original_plus_necessity(self):
        text = role("epic_breakdown_reviewer")
        m = re.search(r'"area": "([^"]+)"', text)
        areas = m.group(1).split("|")
        self.assertEqual(areas, ["coverage", "ticket_size", "domain_split", "checklist", "verification",
                                 "dependency", "sequencing", "overlap", "tracker", "necessity"])

    def test_prefix_literals_shared_by_reviewers_and_producers(self):
        for literal in ("[optional]", "[deferred]"):
            for name in REVIEWERS + PRODUCERS:
                self.assertIn(literal, role(name), f"{name}: {literal}")
        self.assertIn("[scope-concern]", role("epic_breakdown_reviewer"))
        self.assertIn("[scope-concern]", role("epic_planner"))
        self.assertIn("[out-of-scope]", role("architect_reviewer"))

    def test_materiality_mapping_and_approval_principle(self):
        for name in REVIEWERS:
            low = role(name).lower()
            self.assertIn("approve when", low, name)
            self.assertIn("`[optional]`", low, name)
            self.assertIn("`[deferred]`", low, name)
            self.assertRegex(low, r"never block", name)

    def test_breakdown_origin_split(self):
        text = role("epic_breakdown_reviewer")
        self.assertIn("never a reason for `request_changes` on its own", text)
        self.assertIn("never forces `block`", text)
        self.assertIn("Planner-originated excess", text)
        self.assertIn("May cause `request_changes`", text)
        self.assertIn("Design-originated excess", text)
        self.assertIn("If unsure which origin applies, use (b)", text)
        for q in range(1, 8):
            self.assertIn(f"Q{q}:", text)
        self.assertIn("A missing optional enhancement is not a defect", text)

    def test_analysis_reviewer_scope_inflation_question(self):
        text = role("epic_analysis_reviewer")
        self.assertIn("Does the analysis introduce capabilities not justified by the original epic?", text)
        self.assertIn("Do not introduce new product requirements", text)

    def test_design_reviewer_rules(self):
        text = role("epic_reviewer")
        self.assertIn("Do not introduce new business requirements", text)
        for point in FIVE_POINT:
            self.assertIn(point, text)
        self.assertIn("scope|architecture|dependency|sequencing|risk|rollout", text)


class ProducerContractTests(unittest.TestCase):
    def test_fix_round_precedence_sentence(self):
        for name in PRODUCERS:
            text = role(name)
            self.assertIn("takes precedence over any \"address medium and low where feasible\" wording", text, name)

    def test_five_point_justification(self):
        for name in ("epic_designer", "epic_planner"):
            low = role(name).lower()
            for point in FIVE_POINT:
                self.assertIn(point, low, f"{name}: {point}")

    def test_planner_required_content(self):
        text = role("epic_planner")
        for needle in ("## Domains", "## Domain Checklist", "## Verification", "## Quality Notes",
                       "per-domain", "per-layer",
                       "one independently verifiable feature/outcome per ticket, spanning all needed domains",
                       "Decision A", "Decision B", "Scope Necessity Check",
                       "Do not optimize for ticket count",
                       "at the latest milestone and raise under QUESTIONS",
                       "`## Deferred`", "not a new artifact or workflow state",
                       "Reuse the epic's own milestones"):
            self.assertIn(needle.lower(), text.lower(), needle)
        self.assertLess(text.index("Decision A"), text.index("## 2. Tickets"))
        self.assertLess(text.index("BACKLOG REDUCTION PASS"), text.index("## 2. Tickets"))

    def test_planner_deferred_never_holds_approved_requirements(self):
        self.assertIn("an approved requirement or mandatory invariant must never be listed there", role("epic_planner"))
        self.assertIn("approved requirement or mandatory invariant", role("epic_breakdown_reviewer"))

    def test_designer_structure(self):
        text = role("epic_designer")
        self.assertLess(text.index("MINIMUM VIABLE ARCHITECTURE"), text.index("## 1. Proposed Solution"))
        for n, title in enumerate(("Proposed Solution", "Architecture / System Impact",
                                   "Modules / Components Affected", "Data / API / Integration Changes",
                                   "Rollout / Migration Strategy", "Sequencing Strategy",
                                   "Risks / Trade-offs", "Open Questions"), start=1):
            self.assertIn(f"## {n}. {title}", text)
        self.assertIn("distiller stage turns this section into ADRs", text)
        self.assertIn(".ai/epics/<EPIC>/design/epic_design.md", text)
        self.assertNotIn("For each significant decision, state the alternatives", text)

    def test_analyst_keeps_ten_sections(self):
        text = role("epic_analyst")
        titles = ("Problem Statement", "Business Goal", "Success Criteria", "Scope", "Out of Scope",
                  "Stakeholders / Affected Areas", "Cross-Domain Dependencies", "External Dependencies",
                  "Key Risks", "Assumptions / Unknowns")
        positions = []
        for n, title in enumerate(titles, start=1):
            heading = f"## {n}. {title}"
            self.assertIn(heading, text)
            positions.append(text.index(heading))
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("## 11.", text)
        for tag in ("ESSENTIAL", "GUARDRAIL", "DEFERRABLE", "confirmed", "inferred"):
            self.assertIn(tag, text)

    def test_architect_contracts(self):
        text = role("architect")
        for needle in ("task_spec.md", "design_note.md", "acceptance_criteria.md", "assumptions.md",
                       "## Domain Checklist", "## Verification", "Wrapper path"):
            self.assertIn(needle, text)
        self.assertIn("Escalate only decisions that", text)
        self.assertIn("Raise only points that meet an ASSUMPTION DISCIPLINE escalation criterion", text)

    def test_developer_contracts(self):
        text = role("developer")
        for needle in ("## Verification Evidence", "## Architecture Impact", "Code comments:",
                       "git commit -m"):
            self.assertIn(needle, text)

    def test_distiller_contracts(self):
        text = role("distiller")
        self.assertEqual(text.count("ADR NECESSITY RULE"), 2)
        self.assertLess(text.index("ADR NECESSITY RULE (both modes)"), text.index("## Mode: Ticket-land"))
        for needle in ("Writing zero ADRs is valid", "Do not create one ADR per numbered design decision",
                       "`[FLAG]`", "`[PRUNE]`", "## ADR Index", "Do NOT run `git add`"):
            self.assertIn(needle, text)


class FixPromptAssemblyTests(base.EpicProject):
    PRECEDENCE = "takes precedence over any \"address medium and low where feasible\" wording"

    def request_changes(self):
        return [{"severity": "high", "area": "a", "message": "mm"}]

    def test_role_text_reaches_prompts_and_fix_prompts(self):
        self.write_analysis()
        self.write_design()
        self.write_breakdown()

        self.write_review("analysis", "request_changes", self.request_changes())
        quiet(ai_run.epic_analysis_review_complete, EPIC)
        quiet(ai_run.epic_analysis_fix_prepare, EPIC)
        prompt = ai_run.epic_analysis_fix_prompt_path(EPIC).read_text()
        self.assertIn("MVP SCOPE DISCIPLINE", prompt)
        self.assertIn(self.PRECEDENCE, prompt)

        self.write_design_review("request_changes")
        quiet(ai_run.epic_review_complete, EPIC)
        quiet(ai_run.epic_design_fix_prepare, EPIC)
        prompt = ai_run.epic_design_fix_prompt_path(EPIC).read_text()
        self.assertIn("MINIMUM VIABLE ARCHITECTURE", prompt)
        self.assertIn(self.PRECEDENCE, prompt)
        for point in FIVE_POINT:
            self.assertIn(point, prompt.lower())

        self.write_review("breakdown", "request_changes", self.request_changes())
        quiet(ai_run.epic_breakdown_review_complete, EPIC)
        quiet(ai_run.epic_breakdown_fix_prepare, EPIC)
        prompt = ai_run.epic_breakdown_fix_prompt_path(EPIC).read_text()
        self.assertIn("SCOPE PRESERVATION", prompt)
        self.assertIn(self.PRECEDENCE, prompt)
        for point in FIVE_POINT:
            self.assertIn(point, prompt.lower())

    def test_reviewer_prompts_carry_materiality_text(self):
        self.write_analysis()
        self.write_design()
        self.write_breakdown()
        quiet(ai_run.epic_analysis_review_prepare, EPIC)
        self.assertIn("ANALYSIS REVIEW MATERIALITY", ai_run.epic_analysis_review_prompt_path(EPIC).read_text())
        quiet(ai_run.epic_review_prepare, EPIC)
        self.assertIn("DESIGN REVIEW MATERIALITY", ai_run.epic_review_prompt_path(EPIC).read_text())
        quiet(ai_run.epic_breakdown_review_prepare, EPIC)
        self.assertIn("NECESSITY-FIRST BREAKDOWN REVIEW",
                      ai_run.epic_breakdown_review_prompt_path(EPIC).read_text())

    def test_architect_fix_prompt_carries_precedence(self):
        quiet(ai_run.init_ticket, "T-1", "req")
        for path in (ai_run.input_file("T-1"), ai_run.task_spec_path("T-1"), ai_run.design_note_path("T-1"),
                     ai_run.acceptance_criteria_path("T-1"), ai_run.assumptions_path("T-1")):
            self.w(path, "x")
        quiet(ai_run.architect_fix_prepare, "T-1")
        prompt = ai_run.architect_fix_prompt_path("T-1").read_text()
        self.assertIn("ASSUMPTION DISCIPLINE", prompt)
        self.assertIn(self.PRECEDENCE, prompt)


if __name__ == "__main__":
    unittest.main()
