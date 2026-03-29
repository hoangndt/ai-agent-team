# Skill: Acceptance Tests (Playwright)

Use this skill for:

- acceptance test implementation and maintenance in `acceptance-tests/`
- page object model (POM) pattern in acceptance tests
- test sharding and parallel execution configuration
- CI acceptance test workflow changes (`acceptance_tests.yml`)
- acceptance test debugging (video, screenshot, trace artifacts)

---

## Goals

- Cover critical end-to-end user journeys against the deployed application
- Keep tests stable and independently runnable
- Maintain consistent POM structure across the `acceptance-tests/` folder
- Ensure all failures produce diagnosable artifacts (screenshot, video, trace)

---

## Tech Stack

- Playwright 1.36.2 (TypeScript)
- Page Object Model pattern
- Custom reporter: `playwright.reporter.log.js`
- Blob reporting with HTML report merge across shards
- Sharded execution: 4 shards in CI

---

## Project Structure (acceptance-tests/)

- `pages/` — Page Object Model classes
- `tests/` — test spec files
- `playwright.config.ts` — test configuration (timeout, base URL, reporters)
- Credentials sourced from AWS Secrets Manager in CI

---

## Distinction from webapp E2E tests

- `acceptance-tests/` tests run against the **deployed** application
- `webapp/` unit tests run in isolation with mocked data
- Acceptance tests are the final validation gate before release
- Acceptance tests run on a schedule in CI and on manual trigger

---

## Design Rules

1. Use Page Object Model — do not write raw `page.locator()` calls inline in test specs
2. Each POM class should represent one page or major UI section
3. Use `data-testid` attributes as the primary selector strategy
4. Use explicit Playwright waits — no `waitForTimeout` with fixed durations
5. Each test must be independently runnable (no shared mutable state)
6. Tests that require auth should use a shared auth state fixture, not log in per test
7. Credentials for test environments come from AWS Secrets Manager — not hardcoded

---

## Sharding Rules

- Tests run with 4 shards in CI (`--shard=N/4`)
- Blob reports from each shard are merged into a single HTML report
- Tests must not assume shard-specific execution order
- Long-running tests should be distributed across shards, not clustered

---

## Failure Artifact Rules

- On failure: screenshot + video are captured automatically
- Traces are captured on retry
- Artifacts are uploaded to CI as `playwright-report-shard-N`
- HTML report is generated from merged blob reports

---

## Acceptance Test Checklist

For new or updated acceptance tests, verify:

- test uses POM classes — no inline locators in spec file
- selector strategy uses `data-testid` or accessible roles
- explicit Playwright waits are used for async operations
- test runs independently when executed alone
- test is assigned to the correct shard distribution
- credential/config is sourced from env variables, not hardcoded
- failure produces a clear, diagnosable error message

---

## Output Guidance

When asked to write an implementation report, include:

1. User flows covered by new/updated tests
2. POM classes added or modified
3. Selector strategy used
4. Explicit waits added
5. Files modified

---

## Avoid

- Inline `page.locator()` calls in test spec files (use POM)
- `waitForTimeout` with fixed milliseconds
- Hardcoded credentials or base URLs
- Tests that depend on other tests having run first
- Over-testing implementation details already covered by unit tests
