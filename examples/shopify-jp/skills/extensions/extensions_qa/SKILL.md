# Skill: Shopify Extensions QA

Use this skill for:

- QA review of Shopify UI Extension and Function changes
- identifying missing test scenarios for extension behavior
- validating acceptance criteria coverage for checkout and cart extensions
- assessing regression risk to the checkout flow

---

## QA Priorities

1. acceptance criteria coverage — is every criterion testable?
2. extension target coverage — is every declared target exercised in a test scenario?
3. Function edge cases — empty cart, zero discount, missing metafield
4. checkout regression — does the extension risk breaking the checkout flow?
5. sandbox constraint compliance — no browser globals, no raw HTML

---

## QA Checklist

### UI Extension scenarios

- happy path: extension renders correctly in its target surface
- empty / missing data: extension handles absent cart lines, missing metafields gracefully
- conditional rendering: any show/hide logic is exercised in both states
- localization: translated strings render correctly
- editor compatibility: extension renders correctly in checkout editor preview

### Shopify Function scenarios

- happy path: correct discount/rule applied for qualifying cart
- no-op path: Function returns no changes for a non-qualifying cart
- edge cases: empty cart, single-item cart, cart with ineligible products
- metafield missing: Function degrades gracefully when configuration metafield is absent
- local test run confirmed with `shopify app function run`

### Regression risk

- does the extension modify checkout attributes in a way that could affect order processing?
- does a Function change affect existing active discounts or shipping rules?
- is the TOML target change backward-compatible with the deployed extension version?

---

## Output Guidance

A good QA report should:

- list specific missing test scenarios by extension target or Function type
- call out empty-state and error-state gaps for both UI and Function
- flag checkout regression risks explicitly
- confirm whether local Function testing was evidenced in the implementation report
- say pass or fail with clear reasoning tied to acceptance criteria

---

## Avoid

- marking as fail for cosmetic UI component preferences
- generic "needs more tests" without specifying which Function inputs or UI states
- ignoring Function edge cases — they cause silent incorrect discount applications
- repeating reviewer findings already captured
