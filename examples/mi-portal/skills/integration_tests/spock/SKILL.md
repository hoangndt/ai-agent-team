# Skill: Integration Tests (Spock / Groovy / Gradle)

Use this skill for:

- writing or updating integration tests in `IntegrationTests/`
- Spock specification structure and best practices
- HTTP integration test assertions against the live API
- Gradle build configuration changes for tests
- Allure test report generation
- reviewing integration test coverage gaps

---

## Goals

- Cover critical API contracts with integration-level tests
- Run tests against a real (or realistic) backend — not mocked services
- Keep test specs readable and behavior-driven (Spock BDD style)
- Ensure Allure reports are generated and uploaded as part of CI

---

## Tech Stack

- Gradle 7.x (build tool)
- Groovy 2.5.8 (test language)
- Spock Framework 1.3 (BDD test framework)
- http-builder 0.7.1 (HTTP client for API calls)
- Allure Framework 2.13.5 (test reporting)
- AWS Java SDK 1.11.482 (AWS integration in tests)
- Elasticsearch REST client 6.6.2 (ES assertions)
- JWT (jjwt 0.9.1) for token generation in tests
- ShazamCrest for deep object matching assertions

---

## Spock Structure Rules

1. Use `given / when / then` blocks — keep them clean and readable
2. Name test methods with descriptive, behavior-oriented strings (e.g. `"returns 400 when required field is missing"`)
3. Use `where` tables for parameterized tests
4. Do not share mutable state between `Specification` classes
5. `@Stepwise` specs should be used sparingly — prefer independent tests

---

## HTTP Test Rules

1. Use the shared HTTP client setup rather than creating new client instances per test
2. Assert HTTP status code first, then response body
3. Use ShazamCrest `sameBeanAs` for deep object equality
4. Keep auth token generation in a shared test utility
5. Clean up any test data created during test execution

---

## Checklist

For integration test changes, verify:

- each test covers a clearly stated API behavior
- tests run independently (no implicit ordering dependency)
- auth tokens are generated correctly for the test environment
- assertions are specific — avoid asserting only that response is non-null
- Allure annotations (`@Feature`, `@Story`, `@Step`) are used for report readability
- `build.gradle` changes do not break existing test suite

---

## CI Integration

- Tests are packaged as a zip and deployed via Octopus Deploy (`integration-tests-deploy.yml`)
- Run against deployed API environments
- Allure report generated and stored as artifact

---

## Output Guidance

When asked to write an implementation report, include:

1. Specification class(es) added or modified
2. API behaviors covered
3. Auth/credential setup used
4. Allure annotations applied
5. Files modified

---

## Avoid

- Hardcoding API base URLs — use test config/environment variables
- Tests that depend on execution order
- Overly generic assertions (`!= null`, `size() > 0` without context)
- Leaking credentials or tokens into test output/logs
