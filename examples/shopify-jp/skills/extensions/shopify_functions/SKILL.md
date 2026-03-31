# Skill: Shopify Functions

Use this skill for:

- implementing or modifying Shopify Functions (discounts, shipping, payment, fulfillment)
- writing Function logic in JavaScript (Wasm) or Rust
- defining Function input/output types via GraphQL query
- configuring Functions in `shopify.extension.toml`
- testing Functions locally with `shopify app function run`

---

## Goals

- Keep Function logic pure: same inputs always produce same outputs
- Respect strict execution time limits (5ms for most Function types)
- Keep the input GraphQL query minimal — request only fields the Function actually uses
- Make discount or shipping logic explicit and readable

---

## Function Architecture

- **Location** — inside `apps/jp-custom-discount-app/extensions/<function-name>/`
- **Entry point** — `src/index.js` (JS Wasm via `@shopify/shopify_function`) or `src/main.rs` (Rust)
- **Input query** — `src/run.graphql` defines the GraphQL query for inputs
- **Output** — typed per Function API (e.g., `FunctionRunResult` for discounts)
- **TOML config** — `shopify.extension.toml` declares the Function type and API version (`2024-10`)

---

## Implementation Rules

1. Functions must be **pure** — no network calls, no file I/O, no randomness, no global mutable state
2. Execution time limit is 5ms for most Function APIs — keep logic fast and linear
3. The input GraphQL query must request only fields that are used in the Function logic
4. Never hardcode discount codes or prices — read them from metafields or Function configuration
5. Output must conform exactly to the Function API's expected result type
6. Test every Function locally with `shopify app function run` before marking complete
7. For JavaScript Functions: use `@shopify/shopify_function` package conventions
8. For Rust Functions: keep dependencies minimal; avoid heavy crates that inflate Wasm size
9. Handle edge cases explicitly: empty cart, missing metafields, zero-quantity items
10. Document what each Function does and its expected input/output in the implementation report

---

## Common Function Types

| Function API | Use case |
|---|---|
| `product_discounts` | Percentage/fixed discounts on products |
| `order_discounts` | Order-level discount rules |
| `cart_transform` | Modify cart lines before checkout |
| `shipping_discounts` | Free/discounted shipping rules |
| `payment_customization` | Hide or reorder payment methods |
| `fulfillment_constraints` | Custom fulfillment routing rules |

---

## Input Query Checklist

For the `run.graphql` query, verify:

- only fields actually used in Function logic are requested
- metafield namespaces and keys match what is configured in the app
- cart line fields (quantity, variant, product type, tags) are requested if used
- buyer locale or market is requested if the Function varies by region

---

## Testing Checklist

Before marking a Function complete:

- `shopify app function run` executes without errors against a sample input JSON
- edge cases (empty cart, zero discount, missing metafield) produce valid output
- output structure matches the Function API's expected `FunctionRunResult` shape
- execution time is well below the 5ms limit

---

## Output Guidance

When writing an implementation report, include:

1. Function type and API version
2. Logic summary (what discount/rule is applied and under what conditions)
3. Input fields used (from `run.graphql`)
4. Edge cases handled
5. Test command run and result
6. Files modified

---

## Avoid

- Side effects (network, I/O, randomness) inside Function logic
- Requesting unused fields in the input query (adds unnecessary payload size)
- Hardcoded business rules that should come from metafields or configuration
- Skipping local testing with `shopify app function run`
- Output shapes that don't match the Function API spec
