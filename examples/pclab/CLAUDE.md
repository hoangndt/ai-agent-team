# PcLab AI Workflow Guide

This repository contains:

- `backend/` for the Python/FastAPI backend
- `frontend/` for the frontend application

Current AI workflow focus is backend-first.
Unless explicitly asked otherwise, prioritize backend-related tasks.

---

## Working Model

Use the structured workflow in `.ai/runs/<TICKET>/`.

Typical stages:

1. Architect
2. Developer
3. Reviewer
4. QA

Read and write workflow artifacts inside `.ai/runs/<TICKET>/`.

---

## Repository Priorities

For now, prefer work inside:

- `backend/`

Do not modify `frontend/` unless:

- the task explicitly requires it
- or the backend task depends on a frontend contract change

---

## Backend Stack

Primary backend technologies:

- Python
- FastAPI
- Playwright
- PostgreSQL
- Alembic

When implementing or reviewing backend work:

- prefer existing backend conventions
- keep business logic explicit
- keep database changes intentional and minimal
- treat migrations as first-class artifacts
- separate scraping/browser automation concerns from API/service concerns

---

## General Rules

1. Stay within ticket scope
2. Prefer existing patterns over new abstractions
3. Read files directly from the repository
4. Write required outputs directly to target files
5. Be explicit about assumptions and unknowns
6. Do not invent requirements
7. Keep output structured and concise

---

## Backend-Specific Rules

- Keep FastAPI routers thin
- Put business logic in service-level modules where possible
- Keep DB access explicit and traceable
- Treat Alembic migrations carefully; avoid unnecessary schema churn
- Isolate Playwright/browser logic from API transport logic
- Prefer deterministic selectors and robust waiting strategies in Playwright code
- Handle retries and transient failures explicitly
- Be careful with async/sync boundaries

---

## Output Rules by Role

### Architect

- define scope clearly
- identify affected backend modules
- clarify DB/API/browser implications
- do not write code

### Developer

- implement minimal correct solution
- localize changes
- keep report factual

### Reviewer

- focus on correctness, maintainability, migration safety, and scraping robustness

### QA

- focus on validation, failure paths, retries, data integrity, migration impact, and regression risk

---

## Success Criteria

A task is successful when:

- required files are created correctly
- backend changes are scoped and consistent
- DB changes are safe and intentional
- Playwright logic is robust enough for production use
- the next agent can continue without ambiguity
