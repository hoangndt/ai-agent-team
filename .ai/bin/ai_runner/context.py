"""Skill, Figma, vault and project-context readers plus output verification helpers."""

import re
from pathlib import Path
from typing import Dict, List, Optional

from .constants import AGENTS, BASE, FIGMA_URL_RE
from .paths import input_file
from .state import (
    fail_stage, get_base_branch, load_epic_status, load_project_config, load_status,
    read,
)


def require_agent_file(name: str) -> str:
    content = read(AGENTS / name)
    if not content.strip():
        raise FileNotFoundError(f"Missing .ai/agents/{name}")
    return content.strip()


def file_ref_list(paths: List[Path], require_exists: bool = True) -> str:
    lines = []
    for path in paths:
        if require_exists and not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")
        lines.append(f"- {path.as_posix()}")
    return "\n".join(lines)


def ensure_non_empty_files(paths: List[Path], stage: str, ticket: str) -> None:
    missing = [p.as_posix() for p in paths if not p.exists() or not read(p).strip()]
    if missing:
        fail_stage(ticket, stage, f"Missing files: {', '.join(missing)}")
        raise FileNotFoundError(f"Missing or empty files: {', '.join(missing)}")


def ensure_section_present(path: Path, heading: str, stage: str, ticket: str) -> None:
    body = read(path) if path.exists() else ""
    lines = body.splitlines()
    heading_re = re.compile(r"^" + re.escape(heading) + r"\s*$")
    next_heading_re = re.compile(r"^#{1,2}\s")

    start = None
    for i, line in enumerate(lines):
        if heading_re.match(line):
            start = i + 1
            break

    content_found = False
    if start is not None:
        for line in lines[start:]:
            if next_heading_re.match(line):
                break
            if line.strip():
                content_found = True
                break

    if not content_found:
        msg = f"Missing or empty section '{heading}' in {path.name}"
        fail_stage(ticket, stage, msg)
        raise ValueError(msg)


def get_ticket_domain(ticket: str) -> str:
    s = load_status(ticket)
    if s.get("domain"):
        return s["domain"]
    return load_project_config().get("default_domain", "backend")


def get_ticket_domains(ticket: str) -> List[str]:
    """All domains of a ticket run, primary first."""
    domains = load_status(ticket).get("domains")
    if domains:
        return list(domains)
    return [get_ticket_domain(ticket)]


def get_domain_config(ticket: str) -> Dict:
    config = load_project_config()
    domain = get_ticket_domain(ticket)
    return config.get("domains", {}).get(domain, {})


def get_role_skills(ticket: str, role: str) -> List[Path]:
    config = load_project_config()
    seen: List[str] = []
    for domain in get_ticket_domains(ticket):
        domain_cfg = config.get("domains", {}).get(domain, {})
        for p in domain_cfg.get("skills", {}).get(role, []):
            if p not in seen:
                seen.append(p)
    return [Path(p) for p in seen]


def load_skill_contents(paths: List[Path]) -> str:
    chunks = []
    for path in paths:
        content = read(path).strip()
        if not content:
            continue
        chunks.append(f"## Skill: {path.parent.name}\n\n{content}")
    return "\n\n".join(chunks)


def extract_figma_urls(text: str) -> List[str]:
    if not text:
        return []
    urls = FIGMA_URL_RE.findall(text)
    seen = set()
    result: List[str] = []
    for url in urls:
        normalized = url.strip().rstrip(".,;")
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def get_ticket_figma_urls(ticket: str) -> List[str]:
    return extract_figma_urls(read(input_file(ticket)))


def get_figma_skill_paths(role: str) -> List[Path]:
    base = BASE / "skills" / "common" / "figma"

    role_map = {
        "architect": base / "architect" / "SKILL.md",
        "developer": base / "developer" / "SKILL.md",
        "reviewer": base / "reviewer" / "SKILL.md",
        "qa": base / "qa" / "SKILL.md",
    }

    paths = [base / "base" / "SKILL.md"]
    role_path = role_map.get(role)
    if role_path:
        paths.append(role_path)

    return paths


def dedupe_paths(paths: List[Path]) -> List[Path]:
    seen = set()
    result: List[Path] = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def get_effective_role_skills(ticket: str, role: str) -> List[Path]:
    paths = list(get_role_skills(ticket, role))

    figma_urls = get_ticket_figma_urls(ticket)
    if figma_urls:
        paths.extend(get_figma_skill_paths(role))

    return dedupe_paths(paths)


def build_figma_context(ticket: str) -> str:
    figma_urls = get_ticket_figma_urls(ticket)
    if not figma_urls:
        return ""

    lines = [
        "# Figma Context",
        "This ticket includes Figma design references.",
        "Use the configured Figma MCP to inspect the linked design before producing your output.",
        "Treat Figma as an important source of truth for visible UI structure when available.",
        "",
        "Figma URLs:",
    ]

    for url in figma_urls:
        lines.append(f"- {url}")

    lines.extend(
        [
            "",
            "Important:",
            "- Inspect Figma before writing the main output.",
            "- If Figma inspection is partial or fails, state that explicitly and continue with best-effort assumptions.",
            "- Summarize relevant findings instead of dumping raw Figma output.",
        ]
    )

    return "\n".join(lines)


def _cap_lines(text: str, cap: int) -> str:
    text = text.strip()
    if not text or cap <= 0:
        return ""
    lines = text.split("\n")
    return "\n".join(lines[:cap])


def vault_root() -> Optional[Path]:
    cfg = load_project_config().get("vault", {})
    if cfg.get("enabled", True) is False:
        return None
    root = Path(cfg.get("path", ".ai/vault"))
    return root if root.is_dir() else None


def next_adr_id() -> str:
    """Next free ADR id, zero-padded to 3 digits; "001" on an empty/missing decisions dir.

    `ADR-NNN-template.md` is skipped naturally: "NNN" isn't 3 digits, so the regex
    below doesn't match it.
    """
    root = vault_root()
    if not root:
        return "001"
    decisions_dir = root / "architecture" / "decisions"
    if not decisions_dir.is_dir():
        return "001"
    max_n = 0
    for path in decisions_dir.iterdir():
        if not path.is_file():
            continue
        match = re.match(r"^ADR-(\d{3})", path.name)
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"{max_n + 1:03d}"


def read_vault_overview() -> str:
    root = vault_root()
    if not root:
        return ""
    cfg = load_project_config().get("vault", {})
    cap = cfg.get("overview_cap_lines", 200)
    text = read(root / "architecture" / "system-overview.md")
    return _cap_lines(text, cap)


def read_vault_modules(domains: List[str], role: str) -> str:
    cfg = load_project_config().get("vault", {})
    inject_roles = cfg.get(
        "inject_modules_for",
        ["architect", "developer", "epic_analyst", "epic_designer", "distiller"],
    )
    if role not in inject_roles:
        return ""
    root = vault_root()
    if not root:
        return ""
    cap = cfg.get("module_cap_lines", 400)
    chunks: List[str] = []
    seen = set()
    for domain in domains:
        if domain in seen:
            continue
        seen.add(domain)
        text = read(root / "architecture" / "modules" / f"{domain}.md")
        text = _cap_lines(text, cap)
        if text:
            chunks.append(text)
    return "\n\n".join(chunks)


def build_vault_context(domains: List[str], role: str) -> str:
    overview = read_vault_overview()
    modules = read_vault_modules(domains, role)
    if not overview and not modules:
        return ""
    parts = ["# Architecture (Vault)"]
    if overview:
        parts.extend(["", "## System Overview", overview])
    if modules:
        parts.extend(["", "## Domain Modules", modules])
    return "\n".join(parts)


def build_project_context(ticket: str) -> str:
    config = load_project_config()
    domain = get_ticket_domain(ticket)
    domains = get_ticket_domains(ticket)
    lines = [
        f"Project: {config.get('project_name', 'Unknown')}",
        f"Domain: {domain}",
    ]
    if len(domains) > 1:
        lines.append(f"Domains: {', '.join(domains)}")
    lines.append(f"Base branch: {get_base_branch()}")
    paths: List[str] = []
    for d in domains:
        for p in config.get("domains", {}).get(d, {}).get("paths", []):
            if p not in paths:
                paths.append(p)
    if paths:
        lines.append("Relevant paths:")
        for p in paths:
            lines.append(f"- {p}")
    return "\n".join(lines)


def get_epic_domains(epic: str) -> List[str]:
    s = load_epic_status(epic)
    if "domains" in s:
        return s["domains"]
    if "domain" in s:
        return [s["domain"]]
    return list(load_project_config().get("domains", {}).keys())


def get_epic_domain(epic: str) -> str:
    """Backward-compat shim — returns the first domain from get_epic_domains.

    Raises ValueError if no domains are available (empty config and no status entry).
    Callers that do config.get('domains', {}).get(domain, {}) would silently receive
    an empty dict if this returned ""; raising here makes the failure explicit.
    """
    domains = get_epic_domains(epic)
    if not domains:
        raise ValueError(
            f"No domains found for epic '{epic}'. "
            "Check status.json and project_config.json to ensure at least one domain is defined."
        )
    return domains[0]


def build_epic_project_context(epic: str) -> str:
    config = load_project_config()
    domains = get_epic_domains(epic)
    lines = [
        f"Project: {config.get('project_name', 'Unknown')}",
        f"Domains: {', '.join(domains)}",
        f"Base branch: {get_base_branch()}",
    ]
    seen_paths: List[str] = []
    for domain in domains:
        domain_cfg = config.get("domains", {}).get(domain, {})
        for p in domain_cfg.get("paths", []):
            if p not in seen_paths:
                seen_paths.append(p)
    if seen_paths:
        lines.append("Relevant paths:")
        for p in seen_paths:
            lines.append(f"- {p}")
    return "\n".join(lines)


def get_epic_role_skills(epic: str, role: str) -> List[Path]:
    config = load_project_config()
    domains = get_epic_domains(epic)
    seen: List[str] = []
    for domain in domains:
        domain_cfg = config.get("domains", {}).get(domain, {})
        for p in domain_cfg.get("skills", {}).get(role, []):
            if p not in seen:
                seen.append(p)
    return [Path(p) for p in seen]
