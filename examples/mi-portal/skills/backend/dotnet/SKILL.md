# Skill: .NET Backend

Use this skill for:

- API controller implementation
- service layer changes
- repository and data access changes
- request/response model updates
- dependency injection configuration
- validation and error handling
- backend refactors within the .NET project

---

## Goals

- Keep controllers thin
- Put business logic in the service layer
- Keep code explicit and maintainable
- Reuse existing repository patterns
- Avoid unnecessary abstractions

---

## Preferred Design

- Controller layer:
  - request parsing and routing
  - auth/authorization wiring
  - response shaping
- Service layer:
  - business rules
  - orchestration
  - validation beyond model annotations
- Repository/data access layer:
  - Snowflake query execution
  - DB-specific logic

---

## Implementation Rules

1. Prefer existing project structure in `backend/`
2. Keep request/response DTOs clear and versioned
3. Validate external input early using model validation or FluentValidation
4. Raise explicit, meaningful exceptions or problem detail responses
5. Do not leak data access models directly into controller responses
6. Keep async usage consistent with the surrounding codebase
7. Follow existing dependency injection registration patterns

---

## API Checklist

When implementing or reviewing an endpoint, check:

- route path is clear and consistent with existing patterns
- HTTP method is appropriate
- request DTO is explicit
- response DTO is explicit
- validation is sufficient
- error responses are consistent with existing API style
- auth/authorization behavior is considered
- logging is meaningful but not noisy
- service boundaries are respected

---

## Output Guidance

When asked to write an implementation report, include:

1. Endpoint or service changed
2. Files modified
3. Key behavior added/changed
4. Validation/error handling added
5. Any Snowflake query changes

---

## Avoid

- fat controllers
- hidden side effects
- silent exception swallowing
- mixing data access logic with business logic
- broad refactors outside scope
