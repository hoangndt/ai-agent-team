# Skill: Backend Reviewer

Use this skill for:

- reviewing .NET backend code changes
- checking controller/service/repository boundaries
- checking Snowflake query safety and cost
- validating implementation against acceptance criteria

---

## Review Priorities

Review in this order:

1. correctness
2. acceptance criteria fit
3. regression risk
4. Snowflake query safety and cost
5. .NET service/controller boundaries
6. maintainability

---

## Review Checklist

### Correctness

- does the implementation actually solve the ticket?
- are edge cases handled?
- are assumptions acknowledged?

### .NET / service boundaries

- are controllers thin enough?
- is business logic placed in the service layer?
- are dependencies and validation clear?
- is error handling consistent with the existing API style?

### Snowflake

- are queries parameterized?
- is SELECT * avoided?
- are large table queries filtered appropriately?
- do schema changes affect downstream consumers (Tableau, other services)?
- are column renames safe for all consumers?

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
  - severe correctness, SQL injection risk, unfiltered large query, or production risk

---

## Issue Writing Guidance

Each issue should be:

- concrete
- actionable
- tied to a file or behavior
- severity-tagged

Prefer:

- "Query on large_table has no WHERE clause — will scan full table on each request"
  Over:
- "Query could be more efficient"
