# Skill: Backend QA

Use this skill for:

- backend QA review
- API scenario coverage
- DB change risk review
- scraping/enrichment scenario review
- regression checklist generation

---

## QA Priorities

Focus on:

1. acceptance criteria coverage
2. missing scenarios
3. failure handling
4. validation gaps
5. data integrity
6. regression risk

---

## QA Checklist

### Functional coverage

- main success path covered
- expected output shape covered
- integration points considered

### Validation

- bad input
- missing input
- malformed input
- unsupported values

### Failure scenarios

- timeout
- dependency failure
- empty result
- unexpected format
- partial extraction
- retry exhaustion

### Data integrity

- DB writes consistent
- schema assumptions valid
- migration side effects considered

### Regression

- adjacent endpoints/features impacted?
- old behavior unintentionally changed?
- background jobs/services affected?

---

## Special Focus for PcLab Backend

When relevant, include:

- async/sync boundary issues
- external site DOM changes
- retry/idempotency behavior
- partial enrichment behavior
- structured logging visibility
- migration rollout risks

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
- generic “need more tests” with no specifics
- ignoring operational failure paths
