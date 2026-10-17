"""Role prompt and fix-context builders."""

import json
from pathlib import Path
from typing import Dict, Optional

from .paths import (
    architect_fix_context_path, architect_review_report_path,
    epic_review_fix_context_path, epic_review_report_path, qa_fix_context_path,
    qa_report_path, review_fix_context_path, review_report_path,
)
from .state import read, set_artifact, set_epic_artifact, write
from .context import (
    build_epic_project_context, build_figma_context, build_project_context,
    build_vault_context, get_effective_role_skills, get_epic_domains,
    get_epic_role_skills, get_ticket_domain, load_skill_contents, require_agent_file,
)


def build_role_prompt(ticket: str, role: str, task_instruction: str) -> str:
    role_file_map = {
        "architect": "architect.md",
        "architect_reviewer": "architect_reviewer.md",
        "developer": "developer.md",
        "reviewer": "reviewer.md",
        "qa": "qa.md",
        "arch_init": "arch_init.md",
        "distiller": "distiller.md",
    }
    # architect_reviewer, arch_init, and distiller reuse the same domain skills as
    # architect — omitting a role from this alias set silently
    # resolves to an empty skill list instead of the intended reuse.
    skills_role = (
        "architect" if role in ("architect_reviewer", "arch_init", "distiller") else role
    )
    role_prompt = require_agent_file(role_file_map[role])
    project_context = build_project_context(ticket)
    skill_content = load_skill_contents(get_effective_role_skills(ticket, skills_role))
    figma_context = build_figma_context(ticket)

    parts = [
        "# Role Instruction",
        role_prompt,
        "",
        "# Project Context",
        project_context,
    ]

    vault_context = build_vault_context([get_ticket_domain(ticket)], role)
    if vault_context:
        parts.extend(["", vault_context])

    if skill_content:
        parts.extend(["", "# Domain Skills", skill_content])

    if figma_context:
        parts.extend(["", figma_context])

    parts.extend(["", "# Task Instruction", task_instruction.strip()])
    return "\n".join(parts) + "\n"


def build_fix_context(ticket: str) -> Optional[Path]:
    path = review_report_path(ticket)
    if not path.exists() or not read(path).strip():
        return None

    try:
        review = json.loads(read(path))
    except Exception:
        return None

    issues = review.get("issues", [])
    if not isinstance(issues, list) or not issues:
        return None

    buckets = {"high": [], "medium": [], "low": [], "unknown": []}
    for item in issues:
        sev = str(item.get("severity", "unknown")).lower()
        if sev not in buckets:
            sev = "unknown"
        buckets[sev].append(item)

    lines = [
        "# Review Fix Context",
        "",
        "Use this file to fix review findings without re-implementing the whole feature.",
        "",
        f"Reviewer decision: {review.get('decision', 'unknown')}",
        "",
    ]

    for sev in ["high", "medium", "low", "unknown"]:
        if not buckets[sev]:
            continue
        lines.append(f"## {sev.capitalize()} Severity Issues")
        for idx, issue in enumerate(buckets[sev], start=1):
            lines.append(f"{idx}. File: {issue.get('file', 'unknown')}")
            lines.append(f"   Issue: {str(issue.get('message', '')).strip()}")
        lines.append("")

    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.extend(["## Reviewer Summary", summary, ""])

    path = review_fix_context_path(ticket)
    write(path, "\n".join(lines).strip() + "\n")
    set_artifact(ticket, "review_fix_context", path)
    return path


def build_qa_fix_context(ticket: str) -> Optional[Path]:
    path = qa_report_path(ticket)
    if not path.exists() or not read(path).strip():
        return None

    try:
        qa = json.loads(read(path))
    except Exception:
        return None

    missing_tests = qa.get("missing_tests", [])
    risks = qa.get("risks", [])
    summary = str(qa.get("summary", "")).strip()

    if not missing_tests and not risks and not summary:
        return None

    lines = [
        "# QA Fix Context",
        "",
        "Use this file to address QA failures, missing tests, real defects, and delivery gaps.",
        "",
        f"QA decision: {qa.get('decision', 'unknown')}",
        "",
    ]

    if missing_tests:
        lines.append("## Missing Tests")
        for idx, item in enumerate(missing_tests, start=1):
            lines.append(f"{idx}. {item}")
        lines.append("")

    if risks:
        lines.append("## Risks Requiring Attention")
        for idx, item in enumerate(risks, start=1):
            lines.append(f"{idx}. {item}")
        lines.append("")

    if summary:
        lines.extend(["## QA Summary", summary, ""])

    path = qa_fix_context_path(ticket)
    write(path, "\n".join(lines).strip() + "\n")
    set_artifact(ticket, "qa_fix_context", path)
    return path


def build_architect_fix_context(ticket: str) -> Optional[Path]:
    path = architect_review_report_path(ticket)
    if not path.exists() or not read(path).strip():
        return None

    try:
        review = json.loads(read(path))
    except Exception:
        return None

    issues = review.get("issues", [])
    if not isinstance(issues, list):
        issues = []

    buckets: Dict[str, list] = {"high": [], "medium": [], "low": [], "unknown": []}
    for item in issues:
        sev = str(item.get("severity", "unknown")).lower()
        if sev not in buckets:
            sev = "unknown"
        buckets[sev].append(item)

    lines = [
        "# Architect Review Fix Context",
        "",
        "Use this file to fix architect review findings and update the design artifacts.",
        "",
        f"Reviewer decision: {review.get('decision', 'unknown')}",
        "",
    ]

    for sev in ["high", "medium", "low", "unknown"]:
        if not buckets[sev]:
            continue
        lines.append(f"## {sev.capitalize()} Severity Issues")
        for idx, issue in enumerate(buckets[sev], start=1):
            area = issue.get("area", issue.get("file", "unknown"))
            lines.append(f"{idx}. Area: {area}")
            lines.append(f"   Issue: {str(issue.get('message', '')).strip()}")
        lines.append("")

    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.extend(["## Reviewer Summary", summary, ""])

    ctx_path = architect_fix_context_path(ticket)
    write(ctx_path, "\n".join(lines).strip() + "\n")
    set_artifact(ticket, "architect_fix_context", ctx_path)
    return ctx_path


def build_epic_role_prompt(epic: str, role: str, task_instruction: str) -> str:
    role_file_map = {
        "epic_analyst": "epic_analyst.md",
        "epic_designer": "epic_designer.md",
        "epic_reviewer": "epic_reviewer.md",
        "epic_planner": "epic_planner.md",
        "distiller": "distiller.md",
    }
    # distiller reuses architect domain skills on the epic side too, mirroring the
    # ticket-side alias in build_role_prompt — omitting it silently resolves to an
    # empty skill list instead of the intended reuse.
    skills_role = "architect" if role == "distiller" else role
    role_prompt = require_agent_file(role_file_map[role])
    project_context = build_epic_project_context(epic)
    skill_content = load_skill_contents(get_epic_role_skills(epic, skills_role))
    parts = [
        "# Role Instruction",
        role_prompt,
        "",
        "# Project Context",
        project_context,
    ]

    vault_context = build_vault_context(get_epic_domains(epic), role)
    if vault_context:
        parts.extend(["", vault_context])

    if skill_content:
        parts.extend(["", "# Domain Skills", skill_content])
    parts.extend(["", "# Task Instruction", task_instruction.strip()])
    return "\n".join(parts) + "\n"


def build_epic_review_fix_context(epic: str) -> Optional[Path]:
    path = epic_review_report_path(epic)
    if not path.exists() or not read(path).strip():
        return None

    try:
        review = json.loads(read(path))
    except Exception:
        return None

    issues = review.get("issues", [])
    if not isinstance(issues, list) or not issues:
        return None

    buckets: Dict[str, list] = {"high": [], "medium": [], "low": [], "unknown": []}
    for item in issues:
        sev = str(item.get("severity", "unknown")).lower()
        if sev not in buckets:
            sev = "unknown"
        buckets[sev].append(item)

    lines = [
        "# Epic Review Fix Context",
        "",
        "Use this file to fix epic design review findings.",
        "",
        f"Reviewer decision: {review.get('decision', 'unknown')}",
        "",
    ]

    for sev in ["high", "medium", "low", "unknown"]:
        if not buckets[sev]:
            continue
        lines.append(f"## {sev.capitalize()} Severity Issues")
        for idx, issue in enumerate(buckets[sev], start=1):
            area = issue.get("area", issue.get("file", "unknown"))
            lines.append(f"{idx}. Area: {area}")
            lines.append(f"   Issue: {str(issue.get('message', '')).strip()}")
        lines.append("")

    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.extend(["## Reviewer Summary", summary, ""])

    ctx_path = epic_review_fix_context_path(epic)
    write(ctx_path, "\n".join(lines).strip() + "\n")
    set_epic_artifact(epic, "epic_review_fix_context", ctx_path)
    return ctx_path
