# Skill: Playwright E2E Testing

Use this skill for:

- E2E test implementation for Angular UI
- user flow coverage
- critical path regression tests
- UI interaction and assertion logic
- test reliability improvements

---

## Goals

- Cover critical user paths with stable, maintainable tests
- Minimize flaky behavior
- Prefer deterministic selectors
- Make test failures observable and diagnosable

---

## Design Rules

1. Use `data-testid` attributes as the primary selector strategy
2. Do not rely on CSS class names or element positions for selectors
3. Keep page object models or helper abstractions consistent with codebase patterns
4. Prefer explicit waits over fixed timeouts
5. Each test should be independently runnable
6. Do not share mutable state between tests

---

## Selector Rules

Prefer:

- `data-testid` attributes
- accessible roles and labels (`getByRole`, `getByLabel`)
- stable text content for non-dynamic labels

Avoid:

- nth-child selectors
- selectors tied to layout or cosmetic classes
- deeply nested DOM chains

---

## Reliability Checklist

For each E2E test, verify:

- selector strategy is stable
- explicit waits are used for async operations
- test does not depend on test execution order
- loading states are awaited before assertions
- failure message is clear enough to diagnose

---

## Coverage Guidance

Prioritize tests for:

- critical user flows (authentication, key workflows)
- LaunchDarkly flag toggle scenarios where applicable
- Tableau embed visibility / load state
- form submission success and error paths
- navigation and routing behavior

---

## Output Guidance

When asked to write an implementation report, include:

1. Flows covered by new/updated tests
2. Selector strategy used
3. Key assertions
4. Any explicit waits or setup needed
5. Files modified

---

## Avoid

- flaky waits (fixed `setTimeout`, `waitForTimeout`)
- tests that depend on external services without mocking
- over-testing implementation details
- duplicating unit test coverage in E2E tests
