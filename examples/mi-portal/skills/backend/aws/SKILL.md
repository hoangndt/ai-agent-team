# Skill: AWS Integration

Use this skill for:

- AWS S3 file storage (report exports, customer config)
- AWS Secrets Manager for credential retrieval
- AWS KMS for encryption/decryption
- AWS MWAA (Managed Airflow) for ETL orchestration triggers
- AWS IAM role-based authentication
- AWS CloudWatch logging integration

---

## Goals

- Keep AWS SDK calls in the data access layer (`DataAccess.Aws`)
- Retrieve secrets via Secrets Manager — never hardcode credentials
- Use IAM role-based auth wherever possible
- Keep S3 operations explicit and bucket-scoped

---

## Design Rules

1. All AWS SDK calls belong in `Nrc.MarketInsights.DataAccess.Aws` — do not scatter them across service layers
2. Retrieve secrets from `AWSSDK.SecretsManager` at startup or per-request as needed; cache if safe to do so
3. Never log secret values or credential material
4. S3 bucket names and paths must come from config (`appsettings.json` or environment), not be hardcoded
5. Use structured exception handling for AWS service failures — surface meaningful error messages
6. KMS-encrypted data must be decrypted in the data access layer only

---

## S3 Checklist

For S3 operations, verify:

- bucket name comes from configuration (`nrc-d-bi-report-exports`, `nrc-mi`, etc.)
- object keys are explicit and deterministic
- upload/download errors are caught and surfaced meaningfully
- multipart upload is considered for large report exports
- object ACL / permissions are appropriate

---

## Secrets Manager Checklist

For Secrets Manager usage, verify:

- secret ID comes from configuration, not hardcoded
- secret retrieval failure is handled gracefully
- secrets are not logged or returned to clients
- relevant secrets: `mi-portal-snowflake-connection-secret`, `mi-portal-mssql-hcmg-*`, `mi-portal-launch-darkly-sdk-secret`, `mi-portal-smtp-credentials-secret`

---

## CloudWatch Logging

- NLog is configured to ship logs to CloudWatch via `AWS.Logger.NLog`
- Log groups: `/nrc/dev/mi/bi/portal2` (application), `/nrc/dev/mi/bi/performance2` (performance)
- Do not add new log groups without coordination — use existing ones
- Do not log PII or credential material

---

## MWAA / Airflow

- AWSSDK.MWAA is used to trigger ETL jobs
- Airflow environment name comes from config
- Only trigger; do not poll for job completion in request path — use async patterns

---

## Avoid

- Hardcoded bucket names, secret IDs, or region strings outside of config
- AWS SDK calls outside the `DataAccess.Aws` project
- Logging secrets or credentials
- Synchronous blocking calls to AWS services in request handlers without timeout protection
