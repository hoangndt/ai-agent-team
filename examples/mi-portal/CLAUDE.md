# MiPortal AI Workflow Guide

This repository is a full-stack monorepo containing:

- `webapp/` — Angular 18 frontend application
- `api/` — .NET 8 backend (ASP.NET Core)
- `acceptance-tests/` — Playwright acceptance tests (run against deployed app)
- `IntegrationTests/` — Gradle/Spock/Groovy integration tests
- `spiceai-middleware/` — SpiceAI data middleware (Snowflake → gRPC Flight)
- `wiremock/` — WireMock mock API server mappings

Current AI workflow default domain is **frontend**.
Unless explicitly asked otherwise, prioritize frontend-related tasks.

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

- `webapp/`

Do not modify `api/` unless:

- the task explicitly requires it
- or the frontend task depends on a backend contract change

---

## Frontend Stack (`webapp/`)

Primary technologies:

- Angular 18.2 (TypeScript 5.5)
- RxJS 7, Bootstrap 5, Angular Material 17
- LaunchDarkly JS Client SDK 2.19 (feature flags)
- Amplitude Analytics 2.27 + Session Replay plugin (analytics)
- Tableau embedded reports (Tableau JS SDK)
- D3.js 5 (data visualization)
- Leaflet 1.8 (mapping)
- Playwright 1.36 (E2E via `acceptance-tests/`)
- Karma + Jasmine (unit tests)

When implementing or reviewing frontend work:

- prefer existing Angular module/component conventions
- keep component logic minimal; delegate to services
- treat LaunchDarkly flags as first-class — never hardcode feature toggles
- keep Tableau embed logic isolated from business components
- centralize Amplitude tracking calls in an `AnalyticsService` — never call SDK directly from components
- use Playwright for E2E tests against real browser behavior

---

## Backend Stack (`api/`)

Primary technologies:

- .NET 8.0 (ASP.NET Core, C#)
- Dapper (micro-ORM)
- FluentValidation 12, AutoMapper 15
- Snowflake (Snowflake.Data 4.7 — primary data warehouse)
- SQL Server / MSSQL (System.Data.SqlClient 4.9)
- Vertica (JDBC 9.2, legacy data source)
- AWS SDK: S3, Secrets Manager, KMS, MWAA (Airflow)
- SpiceAI 0.2 SDK (data abstraction layer over Snowflake)
- ClosedXML 0.105, CsvHelper 33 (report exports → S3)
- LaunchDarkly Server SDK 8.10 (feature flags)
- NewRelic 9.7 (APM monitoring)
- NLog 4.7 + AWS CloudWatch (logging)

Project structure follows Clean Architecture:
- `Nrc.MarketInsights.Api` (controllers)
- `Nrc.MarketInsights.App` (services / business logic)
- `Nrc.MarketInsights.Domain` (models / interfaces)
- `Nrc.MarketInsights.DataAccess.*` (Snowflake, MsSql, SpiceAI, Aws, Vertica)
- `Nrc.MarketInsights.Excel`, `ReportExport`, `ReportExport.Pdf`, `ReportExport.Csv`

When implementing or reviewing backend work:

- keep controllers thin; delegate to service layer
- treat Snowflake queries carefully — avoid unnecessary full scans
- be explicit about query cost and schema assumptions
- AWS credentials come from Secrets Manager — never hardcode
- report exports go to S3 bucket `nrc-d-bi-report-exports`

---

## Acceptance Tests (`acceptance-tests/`)

- Playwright 1.36 (TypeScript)
- Page Object Model pattern
- Run against the **deployed** application (not mocked)
- 4-shard parallel execution in CI
- Credentials from AWS Secrets Manager

---

## Integration Tests (`IntegrationTests/`)

- Gradle 7 + Groovy 2.5 + Spock 1.3
- HTTP integration tests against live API
- Allure Framework for test reporting
- Deployed via Octopus Deploy

---

## SpiceAI Middleware (`spiceai-middleware/`)

- SpiceAI data middleware connecting to Snowflake (account: NRC.DEV)
- gRPC Flight endpoint on port 50051
- Tableau SQL query files in `spiceai-middleware/tableau-sql/`
- Config via `.env` (never commit credentials)

---

## CI/CD (`.github/workflows/`)

| Workflow | Purpose |
|---|---|
| `acceptance_tests.yml` | Playwright acceptance tests (scheduled + manual) |
| `api-build.yml` | .NET build → SonarCloud → ECR → Octopus Deploy |
| `webapp-build.yaml` | Angular production build → Octopus Deploy |
| `webapp-tests.yaml` | Angular lint + unit tests + SonarCloud |
| `integration-tests-deploy.yml` | Gradle test package → Octopus Deploy |

Infrastructure: GitHub Actions, AWS ECR, Octopus Deploy, OpenVPN, SonarCloud, Anchore

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

## Frontend-Specific Rules

- Keep Angular components focused on a single responsibility
- Put business logic in services, not components or templates
- Do not scatter LaunchDarkly flag evaluation across templates
- Keep Tableau embed configuration centralized
- Centralize Amplitude analytics calls — no SDK calls in components
- Playwright tests must target stable selectors — prefer `data-testid` attributes
- Handle async data loading states (loading / error / empty) explicitly

---

## Backend-Specific Rules

- Keep .NET controllers thin
- Put business logic in service layer
- Keep Snowflake queries explicit and parameterized — no SELECT *
- Keep MSSQL queries in `DataAccess.MsSql` — parameterized via Dapper
- Avoid SELECT * in Snowflake and MSSQL queries
- Be careful with warehouse size assumptions; avoid runaway queries
- Document any query that touches large tables
- AWS credentials always from Secrets Manager — never hardcoded
- Report exports go to S3; never return large binary directly without streaming
- SpiceAI Tableau SQL files must stay in sync with Snowflake schema changes

---

## Output Rules by Role

### Architect

- define scope clearly
- identify affected modules, components, services, and data access layers
- clarify API contracts, flag dependencies, Tableau/SpiceAI config implications
- identify AWS resource impacts (S3, Secrets Manager, CloudWatch)
- do not write code

### Developer

- implement minimal correct solution
- localize changes
- keep report factual

### Reviewer

- focus on correctness, component boundaries, flag safety, query cost, and security
- check AWS credential handling and S3 object key safety

### QA

- focus on E2E coverage, flag toggle scenarios, embed states, export correctness, and failure paths
- include Amplitude event fire validation where relevant

---

## Success Criteria

A task is successful when:

- required files are created correctly
- changes are scoped and consistent
- LaunchDarkly flags are used correctly and not hardcoded
- Amplitude events fire correctly and contain no PII
- Playwright tests cover critical user paths
- Snowflake and MSSQL queries are parameterized and not over-scanning
- AWS credentials are sourced from Secrets Manager
- the next agent can continue without ambiguity
