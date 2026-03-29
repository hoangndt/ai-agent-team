# Skill: Backend QA

Use this skill for:

- backend QA review
- API scenario coverage
- Snowflake query risk review
- data integrity scenario review
- regression checklist generation

---

## QA Priorities

Focus on:

1. acceptance criteria coverage
2. missing scenarios
3. failure handling
4. validation gaps
5. data integrity
6. Snowflake query cost risk
7. regression risk

---

## QA Checklist

### Functional coverage

- main success path covered
- expected response shape covered
- integration points with Snowflake considered

### Validation

- bad input
- missing input
- malformed input
- unsupported values

### Failure scenarios

- Snowflake query timeout or failure
- empty result set
- unexpected result format
- downstream service failure
- partial data response

### Data integrity

- Snowflake writes consistent
- schema assumptions valid
- view or column changes do not break downstream consumers

### Snowflake cost risk

- large table queries have appropriate filters
- warehouse size appropriate for query frequency
- no accidental full scans introduced

### Regression

- adjacent endpoints or features impacted?
- old behavior unintentionally changed?
- Tableau report or other consumers affected by schema/view changes?

---

## Special Focus for MiPortal Backend

When relevant, include:

- Snowflake query scan cost on large tables
- Tableau downstream impact of schema/view changes
- .NET async/sync boundary issues
- missing authorization checks on new endpoints
- LaunchDarkly flag state affecting backend behavior (if applicable)

---

## Output Guidance

A good QA report should:

- identify concrete missing tests
- identify concrete risks
- clearly say pass or fail
- stay focused on delivery risk, not coding style

---

## Avoid

- repeating reviewer comments that are purely stylistic
- generic "need more tests" with no specifics
- ignoring Snowflake query cost or scan risk
- ignoring downstream consumer impact of schema changes
