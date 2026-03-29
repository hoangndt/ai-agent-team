# Skill: Frontend QA

Use this skill for:

- frontend QA review
- Angular UI scenario coverage
- LaunchDarkly flag toggle scenario review
- Tableau embed scenario review
- Playwright E2E coverage gaps
- regression checklist generation

---

## QA Priorities

Focus on:

1. acceptance criteria coverage
2. missing scenarios
3. failure handling
4. flag toggle edge cases
5. embed load/error states
6. regression risk

---

## QA Checklist

### Functional coverage

- main success path covered
- expected UI output verified
- integration points with backend considered

### Validation

- form validation edge cases
- invalid/empty input handling
- unsupported value handling

### Failure scenarios

- API failure or timeout
- LaunchDarkly SDK unavailable (flag fallback behavior)
- Tableau embed fails to load
- network error during data fetch
- empty data state
- partial data state

### LaunchDarkly scenarios

- flag-on path works as expected
- flag-off path works as expected (default behavior preserved)
- flag evaluation returns unexpected type
- SDK initialization delay

### Tableau scenarios

- viz loads successfully
- viz fails to load (error state shown)
- filters/parameters applied correctly
- viz destroyed cleanly on navigation away

### Regression

- adjacent components or routes impacted?
- shared services affected?
- routing changes affect existing navigation?
- flag changes affect other flag-gated features?

---

## Special Focus for MiPortal Frontend

When relevant, include:

- LaunchDarkly flag fallback safety
- Tableau embed lifecycle on route change
- Angular async pipe subscription cleanup
- Playwright selector stability
- Loading state visibility to users

---

## Output Guidance

A good QA report should:

- identify concrete missing scenarios
- identify concrete risks
- clearly say pass or fail
- stay focused on delivery risk, not coding style

---

## Avoid

- repeating reviewer comments that are purely stylistic
- generic "need more tests" with no specifics
- ignoring flag-off failure paths
- ignoring Tableau embed error paths
