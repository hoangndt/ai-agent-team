# Skill: PostgreSQL + Alembic

Use this skill for:

- schema changes
- migration design
- DB constraint changes
- index changes
- column additions/removals
- data backfill planning tied to migrations

---

## Goals

- Keep migrations safe, intentional, and reviewable
- Preserve backward compatibility where possible
- Minimize production risk
- Make DB changes easy to reason about

---

## Migration Rules

1. Every schema change must be explicit
2. Avoid unnecessary migration churn
3. Prefer additive changes over destructive changes
4. Treat renames carefully; document impact
5. Consider rollback implications
6. Consider data migration separately from schema migration when needed
7. Keep migration intent obvious from code and report

---

## PostgreSQL Checklist

For DB-related work, check:

- correct column types
- nullability is intentional
- default values are intentional
- indexes support expected query paths
- constraints reflect real business rules
- compatibility with existing data is considered
- read/write path impact is understood

---

## Alembic Checklist

When generating or reviewing migrations, verify:

- migration only contains intended changes
- autogenerate noise is removed
- naming is clear
- downgrade path is reasonable if required by team practice
- data backfill steps are explicit if needed
- model code and migration stay in sync

---

## Risk Areas

Pay extra attention to:

- non-null additions on populated tables
- enum/type changes
- large table rewrites
- dropping columns or constraints
- index creation on large tables
- concurrent access / rollout timing

---

## Output Guidance

DB-related notes should state:

1. what schema changed
2. why it changed
3. migration risk
4. compatibility concerns
5. any manual rollout or backfill concerns

---

## Avoid

- blindly trusting Alembic autogenerate output
- mixing unrelated schema changes in one migration
- destructive migrations without explicit justification
- implicit behavior that is not documented
