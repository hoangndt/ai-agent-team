# Skill: Shopify Extensions Reviewer

Use this skill for:

- reviewing Shopify UI Extension implementations
- reviewing Shopify Function logic
- validating `shopify.extension.toml` configuration
- checking extension API usage and sandbox constraints

---

## Review Priorities

1. correctness — does the extension render or execute as intended?
2. sandbox compliance — no browser globals, no raw HTML, no direct fetch
3. TOML completeness — targets declared match targets rendered
4. Function purity — no side effects, correct output shape
5. acceptance criteria fit
6. performance — component tree depth, Function execution time

---

## Review Checklist

### UI Extensions

- are only `@shopify/ui-extensions-react` components used (no raw HTML)?
- is `window`, `document`, or any browser global accessed? (must not be)
- are all extension targets in TOML matched by rendered components?
- is `useTranslate` used for all customer-facing strings?
- are Shopify API hooks (`useCartLines`, `useApplyAttributeChange`, etc.) used for data access instead of `fetch`?
- is the component tree reasonably shallow?
- are capabilities checked with `useExtensionCapability` before being called?

### Shopify Functions

- is the Function logic pure (no network, I/O, or randomness)?
- does the output shape match the Function API spec?
- does the input query (`run.graphql`) request only needed fields?
- are edge cases (empty cart, missing metafield, zero quantity) handled?
- has local testing with `shopify app function run` been confirmed in the report?
- is execution time expected to be well within the 5ms limit?

### TOML

- is `type` set correctly for the extension?
- is `api_version` specified?
- do `[[extensions.targeting]]` entries match what the code renders?

---

## Decision Guidance

- approve:
  - extension is sandbox-compliant, TOML is complete, Function is pure
- request_changes:
  - untranslated strings, missing TOML targets, Function edge cases not handled
- block:
  - browser global access in UI Extension
  - Function output does not match API spec
  - TOML target declared but no matching render in code

---

## Avoid

- approving UI Extensions that use raw HTML elements
- ignoring missing TOML targets — they cause Shopify CLI validation errors
- treating Function side effects as minor — they will cause runtime failures
