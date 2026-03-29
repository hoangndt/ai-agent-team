# Skill: Backend Reviewer

Use this skill for:

- reviewing backend code changes
- checking FastAPI/service/repository boundaries
- checking Playwright robustness
- checking PostgreSQL/Alembic safety
- validating implementation against acceptance criteria

---

## Review Priorities

Review in this order:

1. correctness
2. acceptance criteria fit
3. regression risk
4. DB/migration safety
5. scraping/browser robustness
6. maintainability

---

## Review Checklist

### Correctness

- does the implementation actually solve the ticket?
- are edge cases handled?
- are assumptions acknowledged?

### FastAPI / service boundaries

- are routers thin enough?
- is business logic placed appropriately?
- are dependencies and validation clear?

### Playwright / scraping

- are waits/selectors robust?
- is failure behavior defined?
- are retries/fallbacks reasonable?

### PostgreSQL / Alembic

- is the migration necessary?
- is the migration safe?
- does schema align with code changes?
- is there backward compatibility risk?

### Maintainability

- is code localized and understandable?
- are abstractions justified?
- is logging useful?

---

## Decision Guidance

- approve:
  - no meaningful issues
- request_changes:
  - fixable but real issues remain
- block:
  - severe correctness, migration, or production risk

---

## Issue Writing Guidance

Each issue should be:

- concrete
- actionable
- tied to a file or behavior
- severity-tagged

Prefer:

- “Missing handling for empty search result causes wrong success path”
  Over:
- “Could be improved”
