# Skill: SQL Server (MSSQL) Data Access

Use this skill for:

- MSSQL data access via Dapper
- SQL Server query implementation and optimization
- stored procedure or view changes in MSSQL
- connection string management via Secrets Manager
- reviewing MSSQL query safety and cost

---

## Goals

- Keep MSSQL queries explicit, parameterized, and readable
- Isolate all MSSQL logic in `DataAccess.MsSql`
- Never concatenate user input into SQL strings
- Avoid SELECT * in production queries

---

## Query Rules

1. Always parameterize user-supplied values — use Dapper parameter objects
2. Never use SELECT * in production queries
3. Be explicit about column names in INSERT/SELECT statements
4. Use transactions where atomicity is required
5. Keep queries in repository methods, not service layer
6. Use async Dapper methods (`QueryAsync`, `ExecuteAsync`) consistently

---

## Connection Management

- Connection strings are retrieved from AWS Secrets Manager
- Relevant secrets: `mi-portal-mssql-hcmg-app-connection-secret`, `mi-portal-mssql-hcmg-dev-connection-secret`
- Do not hardcode connection strings in config files
- Use connection pooling via `SqlConnection` — do not manage pool manually

---

## Checklist

For MSSQL queries and schema changes, verify:

- no SELECT * in production queries
- input is parameterized via Dapper, not concatenated
- query uses appropriate indexes (consider WHERE clause selectivity)
- schema changes are additive where possible
- stored procedure or view changes checked for downstream consumers
- connection string sourced from Secrets Manager

---

## Risk Areas

- SQL injection if query is built with string concatenation
- Large scans on tables without appropriate WHERE clauses
- Schema changes that break existing Dapper column mappings
- Missing transactions for multi-step write operations

---

## Output Guidance

MSSQL-related notes should state:

1. What query or schema changed
2. Parameterization approach
3. Index/performance considerations
4. Downstream impact (API contracts, other repos)

---

## Avoid

- SELECT * in production code
- String-concatenated SQL with user input
- Synchronous Dapper calls when async is available
- Direct SQL in service layer — keep it in repositories
