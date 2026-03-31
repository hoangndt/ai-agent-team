# Skill: Shopify Storefront QA

Use this skill for:

- QA review of Shopify theme changes (Liquid, Tailwind, JS)
- identifying missing test scenarios for storefront features
- validating acceptance criteria coverage for section and template changes
- assessing regression risk to cart, checkout, and existing sections
- checking theme editor compatibility

---

## QA Priorities

Focus on:

1. acceptance criteria coverage — is every criterion testable with the current change?
2. merchant editor compatibility — does the section work correctly in the theme editor?
3. missing scenarios — what customer or merchant flows are not covered?
4. cart and checkout regression — does the change risk breaking cart or checkout behavior?
5. mobile responsiveness — are mobile viewports tested?
6. failure paths — what happens with empty content, missing images, or zero products?

---

## QA Checklist

### Section / Liquid coverage

- happy path: section renders correctly with all settings populated
- empty state: section handles missing images, empty text, or no products gracefully
- theme editor: section reacts correctly to setting changes in the editor
- block limits: max/min block counts enforced correctly
- locale: all keys exist in `en.default.json` and render correctly

### JavaScript coverage

- cart mutation (add/remove/update) succeeds and updates UI
- cart API error responses (out of stock, sold out) are surfaced to the user
- custom element renders correctly when first connected to the DOM (`connectedCallback`)
- custom element cleans up correctly when removed (`disconnectedCallback` / `onDestroy`)
- pub/sub events via `ProductPageStore` fire and are received correctly
- no JS errors in console on page load or interaction
- `assets/core.js` and `assets/product.js` are rebuilt after source changes in `scripts/`

### Tailwind coverage

- layout renders correctly on mobile (320px), tablet (768px), and desktop (1280px)
- no overflow or layout breaks at common viewport sizes

### Regression risk

- does the change modify `theme.liquid` or global snippets that affect every page?
- does the change modify cart behavior that could affect checkout flow?
- are changes localized to the ticket scope without touching unrelated sections?

---

## Output Guidance

A good QA report for this project should:

- list specific missing scenarios by section or flow
- call out empty-state and error-state gaps
- flag theme editor compatibility risks
- identify any global regression risk (layout, cart, checkout)
- say pass or fail with clear reasoning tied to acceptance criteria

---

## Avoid

- marking as fail for cosmetic Tailwind preferences without functional impact
- generic "needs more tests" without specifying which scenarios
- ignoring empty-state handling (blank sections break merchant storefronts)
- repeating reviewer issues already captured
