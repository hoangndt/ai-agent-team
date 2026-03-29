# Skill: SpiceAI Middleware

Use this skill for:

- SpiceAI data layer configuration and query changes
- Tableau SQL query files in `spiceai-middleware/tableau-sql/`
- SpiceAI data source connection updates (Snowflake via ODBC)
- gRPC Flight endpoint configuration
- reviewing SpiceAI query safety and compatibility

---

## Goals

- Keep SpiceAI as a transparent query abstraction layer over Snowflake
- Maintain Tableau SQL queries as versioned, readable files
- Never bypass SpiceAI to hit Snowflake directly unless explicitly required
- Keep SpiceAI config (`spiceai-middleware/`) synchronized with backend data access expectations

---

## Architecture

- SpiceAI runs as a middleware service (gRPC Flight on port 50051)
- Backend uses `Nrc.MarketInsights.DataAccess.SpiceAI` SDK (version 0.2.0) to query SpiceAI
- SpiceAI connects to Snowflake (account: NRC.DEV) via private key authentication
- Tableau SQL queries are stored as `.sql` files in `spiceai-middleware/tableau-sql/`
- Environment config is managed via `.env` file in `spiceai-middleware/`

---

## Query Rules

1. All SpiceAI queries must be parameterized — no raw string concatenation with user input
2. Tableau SQL files in `spiceai-middleware/tableau-sql/` must be kept in sync with any schema changes
3. Column renames in Snowflake must be reflected in SpiceAI Tableau SQL files
4. Avoid SELECT * in SpiceAI queries
5. Test queries against the target Snowflake account before merging

---

## Configuration Rules

- SpiceAI connection config (Snowflake account, private key path) lives in `spiceai-middleware/.env`
- Do not hardcode credentials in SpiceAI config files — use environment variables
- Verify gRPC Flight endpoint is reachable before backend deployment

---

## SpiceAI + Tableau SQL Checklist

For SpiceAI or Tableau SQL changes, verify:

- SQL files updated for any Snowflake schema changes
- No SELECT * used
- Column aliases match what Tableau expects
- Query filters are applied early (not post-select filtering)
- SpiceAI `.env` config is not checked into source control with secrets
- Backend `DataAccess.SpiceAI` queries are compatible with updated SQL

---

## Risk Areas

- Tableau SQL files not updated after Snowflake schema changes → broken Tableau reports
- SpiceAI gRPC service not running → backend data access failures
- Private key rotation not reflected in `.env` → authentication failures
- Unfiltered large queries in Tableau SQL → warehouse cost spikes

---

## Output Guidance

SpiceAI-related notes should state:

1. Which SQL file or config changed
2. Reason for change (schema sync, new Tableau view, etc.)
3. Downstream Tableau report impact
4. Backend `DataAccess.SpiceAI` compatibility verification

---

## Avoid

- Committing private keys or credentials into `spiceai-middleware/.env`
- SELECT * in Tableau SQL queries
- Making schema changes in Snowflake without updating SpiceAI SQL files
- Bypassing SpiceAI to directly query Snowflake from backend when SpiceAI is intended path
