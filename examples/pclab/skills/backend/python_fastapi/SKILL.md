# Skill: Python FastAPI Backend

Use this skill for:

- API endpoint implementation
- service-layer changes
- request/response schema updates
- dependency injection changes
- validation and error handling
- backend refactors within the FastAPI app

---

## Goals

- Keep API handlers thin
- Put business logic in services or domain-oriented modules
- Keep code explicit and maintainable
- Reuse current repository patterns
- Avoid unnecessary abstractions

---

## Preferred Design

- Router layer:
  - request parsing
  - auth/dependency wiring
  - response shaping
- Service layer:
  - business rules
  - orchestration
  - validation beyond basic schema checks
- Repository/data access layer:
  - SQL/ORM interaction
  - DB-specific logic

---

## Implementation Rules

1. Prefer existing module structure in `backend/`
2. Keep request/response models clear and version-safe
3. Validate external input early
4. Raise explicit, meaningful errors
5. Avoid leaking DB models directly across layers unless current repo already does so
6. Keep async usage consistent with the surrounding codebase
7. Do not mix scraping/browser logic into unrelated API modules

---

## API Checklist

When implementing or reviewing an endpoint, check:

- route path is clear
- HTTP method is appropriate
- request schema is explicit
- response schema is explicit
- validation is sufficient
- error cases are handled
- auth/permission behavior is considered if relevant
- logging is meaningful but not noisy
- service boundaries are respected

---

## Output Guidance

When asked to write an implementation report, include:

1. Endpoint or service changed
2. Files modified
3. Key behavior added/changed
4. Validation/error handling added
5. Commands/tests run

---

## Avoid

- fat routers
- hidden side effects
- silent exception swallowing
- mixing transport logic with business logic
- broad refactors outside scope
