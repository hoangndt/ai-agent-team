# Skill: Frontend Reviewer

Use this skill for:

- reviewing Angular component and service changes
- checking LaunchDarkly flag safety
- checking Playwright E2E test quality
- checking Tableau embed correctness
- validating implementation against acceptance criteria

---

## Review Priorities

Review in this order:

1. correctness
2. acceptance criteria fit
3. regression risk
4. Angular component/service boundaries
5. LaunchDarkly flag safety
6. Tableau embed lifecycle
7. Playwright test reliability
8. maintainability

---

## Review Checklist

### Correctness

- does the implementation actually solve the ticket?
- are edge cases handled?
- are assumptions acknowledged?

### Angular boundaries

- are components focused on a single responsibility?
- is business logic in services, not templates?
- are subscriptions cleaned up correctly?
- are loading / error / empty states handled?

### LaunchDarkly

- are flag keys centralized?
- is the fallback value safe and explicit?
- are both flag-on and flag-off paths tested?
- is flag evaluation in the service layer?

### Tableau

- is embed logic isolated from business components?
- are load and error states handled?
- are filters/parameters passed through typed interfaces?
- is viz teardown handled on component destroy?

### Playwright E2E

- are selectors stable (`data-testid` or accessible roles)?
- are explicit waits used?
- is each test independently runnable?
- are assertions meaningful?

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
  - severe correctness, flag safety, or production risk

---

## Issue Writing Guidance

Each issue should be:

- concrete
- actionable
- tied to a file or behavior
- severity-tagged

Prefer:

- "Flag fallback is undefined — component will throw when flag is off"
  Over:
- "Flag handling could be improved"
