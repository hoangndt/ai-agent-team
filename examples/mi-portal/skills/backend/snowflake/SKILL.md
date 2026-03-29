# Skill: Snowflake

Use this skill for:

- query implementation and optimization
- schema or view changes
- stored procedure or task changes
- data access layer updates that interact with Snowflake
- reviewing query cost and safety

---

## Goals

- Keep queries explicit, parameterized, and readable
- Minimize unnecessary warehouse usage
- Avoid full table scans on large tables
- Make schema assumptions visible and documented

---

## Query Rules

1. Never use SELECT * in production queries
2. Always parameterize user-supplied values — do not concatenate input into SQL strings
3. Be explicit about column names in INSERT/SELECT statements
4. Filter early to minimize data scanned
5. Be aware of clustering keys and partition pruning opportunities
6. Use CTEs to keep complex queries readable

---

## Schema Change Rules

1. Every schema change must be explicit and intentional
2. Prefer additive changes (new columns, new views) over destructive changes
3. Document the impact of column renames or type changes
4. Consider downstream consumers (dashboards, Tableau reports) before altering columns
5. Treat view changes carefully — downstream Tableau reports may depend on column names

---

## Snowflake-Specific Checklist

For Snowflake queries and schema changes, verify:

- no SELECT * in production queries
- input is parameterized, not concatenated
- query scans only the required data (filter pushdown considered)
- warehouse size assumption is appropriate for query volume
- large table queries are documented
- view or column changes do not break Tableau or downstream consumers
- clustering/partitioning behavior is understood if relevant

---

## Risk Areas

Pay extra attention to:

- queries without WHERE clauses on large tables
- full warehouse scans triggered by missing filter pushdown
- column renames breaking Tableau reports
- time travel / fail-safe implications for schema changes
- shared views used by multiple consumers

---

## Output Guidance

Snowflake-related notes should state:

1. what query or schema changed
2. why it changed
3. estimated query cost / scan impact
4. compatibility concerns for downstream consumers
5. any rollout or migration concerns

---

## Avoid

- SELECT * in production code
- string-concatenated SQL with user input
- large unfiltered queries without explicit justification
- schema changes without checking Tableau or downstream impact
- implicit type coercions that may behave differently across warehouses
