# Skill: GitHub Actions & Deployment (CI/CD)

Use this skill for:

- modifying or adding GitHub Actions workflows in `.github/workflows/`
- Octopus Deploy integration (package creation and upload)
- SonarCloud code quality scan configuration
- Docker image build and push to AWS ECR
- OpenVPN connection for artifact upload
- acceptance test workflow changes

---

## Goals

- Keep CI/CD workflows minimal and focused on their single concern
- Reuse existing workflow patterns rather than inventing new job shapes
- Never hardcode secrets — use `${{ secrets.* }}` references
- Ensure all workflows have clear failure modes and artifact uploads

---

## Existing Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `acceptance_tests.yml` | schedule / manual | Playwright E2E tests (sharded, 4 parallel) |
| `api-build.yml` | push to release | .NET API build, SonarCloud, ECR push, Octopus Deploy |
| `webapp-build.yaml` | push to release | Angular production build, Octopus Deploy |
| `webapp-tests.yaml` | push to release | Angular lint + unit tests + SonarCloud |
| `integration-tests-deploy.yml` | push to release | Gradle integration test package → Octopus Deploy |

---

## Rules

1. Secrets are referenced via `${{ secrets.* }}` — never hardcode values
2. AWS authentication uses IAM role assumption (`aws-actions/configure-aws-credentials`)
3. OpenVPN 3 is used for VPN connectivity in upload steps — follow existing pattern
4. Octopus Deploy upload uses existing `push-package-to-octopus` step pattern
5. Docker images are tagged with `${{ github.sha }}` for traceability
6. Anchore container scanning runs after Docker build — do not skip

---

## SonarCloud Checklist

For SonarCloud changes, verify:

- project key and organization match existing settings
- coverage report path is correct (`.NET`: `opencover.xml`, `Angular`: `lcov.info`)
- JDK 17 is set up before SonarScanner runs (required for .NET scanner)
- sonar exclusions are appropriate and not hiding real issues

---

## Acceptance Test Workflow

- Docker image: `mcr.microsoft.com/playwright:v1.36.2-jammy`
- Sharded execution: 4 shards (configurable)
- Global timeout: 30 minutes
- AWS Secrets Manager used for test credentials
- Merge blob reports into HTML after all shards complete

---

## Octopus Deploy Package Rules

- Package zip should contain only what is needed for deployment
- Package version should match `${{ github.sha }}` or semantic version
- Upload uses VPN — ensure VPN step precedes upload step

---

## Output Guidance

When asked to write an implementation report on workflow changes, include:

1. Workflow file modified
2. Steps added or changed
3. Secrets or environment variables referenced
4. Impact on existing CI behavior

---

## Avoid

- Hardcoded credentials or tokens in workflow YAML
- Running sensitive steps without proper secret masking
- Modifying workflow files without understanding the VPN / Octopus sequence
- Skipping Anchore or SonarCloud steps without explicit justification
