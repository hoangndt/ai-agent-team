# Skill: Playwright + Checkly (Shopify E2E)

Use this skill for:

- implementing Playwright tests for Shopify storefront customer journeys
- writing Checkly browser checks for production/staging monitoring
- covering critical flows: product discovery, cart, checkout, account
- configuring Checkly checks and groups in code (`checkly.config.ts`)
- test reliability and selector strategy

---

## Goals

- Cover critical customer paths with stable, maintainable tests
- Keep Checkly checks lightweight and resilient to production latency
- Prefer deterministic selectors over positional or cosmetic ones
- Make test failures self-diagnosing

---

## Playwright Design Rules

1. Use `data-testid` attributes as the primary selector strategy
2. Fall back to accessible roles and labels (`getByRole`, `getByLabel`, `getByText`) for stable text
3. Do not use CSS class names, nth-child, or layout-dependent selectors
4. Each test must be independently runnable — no shared mutable state between tests
5. Use `test.describe` to group related flows
6. Use explicit waits (`waitForSelector`, `waitForURL`, `expect(locator).toBeVisible()`) — never `waitForTimeout`
7. Abstract page interactions into Page Object classes and component classes (see POM section below)
8. Store credentials, store URL, and tokens in environment variables — never hardcode

---

## Page Object Model (POM)

### Directory structure

```
e2e/src/
  pages/          # One file per page — extend BasePage
  components/     # Reusable UI components used across pages
  fixtures/       # Playwright fixture wiring (index.ts)
  tests/          # Test files only — no page logic here
  utils/          # Constants, env helpers, URL generators
```

### Class hierarchy

```
BasePage          (src/pages/base.page.ts)
  └── HomePage    (src/pages/home.page.ts)
  └── CollectionPage
  └── ProductPage  — composes AddToCartButton component
  └── CheckoutPage

Components are standalone classes (no BasePage inheritance):
  CartDrawer, CookieBanner, AddToCartButton, …
```

`BasePage` holds shared components (`CartDrawer`, `CookieBanner`) and proxies their methods so every page can call `page.acceptCookie()`, `page.checkout()`, etc. without re-implementing them.

### What belongs where

| Layer | Responsibility | Contains |
|---|---|---|
| **Page class** | A full Shopify page | `goto()`, navigation actions, page-level locators, proxied component methods |
| **Component class** | A reusable UI piece (drawer, button, banner) | Locators scoped to that component, actions, and `expect` assertions for that component |
| **Test file** | Flow orchestration | `test.step`, `expect` calls, fixture injection — no raw `page.locator` calls |
| **Fixture** (`fixtures/index.ts`) | DI wiring | `base.extend` — instantiates page objects and passes them to tests |

### Rules

1. **No `page.locator` in test files** — all selectors live in page or component classes
2. **No `expect` in page classes** — assertions belong in component classes or test files
3. **New page → new file** in `src/pages/`, extending `BasePage`
4. **New reusable UI piece → new file** in `src/components/`, composed into the relevant page class and proxied through `BasePage` if used globally
5. **New page object → register in `fixtures/index.ts`** so tests receive it via fixture injection
6. **Actions return the awaitable** (don't `await` inside page methods) — let the caller decide

### Example: adding a new page

```ts
// src/pages/search.page.ts
import { Page } from "@playwright/test";
import { BasePage } from "./base.page";

export class SearchPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  goto(query: string) {
    return this.page.goto(`/search?q=${encodeURIComponent(query)}`);
  }

  firstResult() {
    return this.page.locator("[data-test='search-result']").first();
  }
}
```

```ts
// fixtures/index.ts — add to StorefrontFixtures and base.extend
searchPage: async ({ page }, use) => {
  await use(new SearchPage(page));
},
```

---

## Checkly Design Rules

1. Checkly checks in `e2e/` are defined as code using `@checkly/cli`
2. Each check must set a `name`, `url` (or script), `frequency`, and `locations`
3. Keep check scripts under ~30 seconds total execution time
4. Checks should degrade gracefully on slow pages — add generous but explicit timeouts
5. Group related checks using `CheckGroup` for shared alerting and scheduling
6. Use `process.env` for all environment-specific values (store URL, test credentials)
7. Tag checks by criticality (`critical`, `smoke`) for selective runs

---

## Critical Shopify Flows to Cover

| Flow | Priority |
|---|---|
| Homepage loads with key sections visible | High |
| Collection page renders products | High |
| Product page: add to cart | Critical |
| Cart: update quantity, remove item | High |
| Checkout: proceed to checkout (guest) | Critical |
| Checkout: apply discount code | High |
| Search: returns relevant results | Medium |
| Account: login and order history | Medium |
| Extension UI renders in checkout | High (if extensions exist) |

---

## Selector Strategy

Preferred (in order):

1. `data-testid` attributes added to Liquid/HTML
2. `getByRole` with accessible name (e.g., `getByRole('button', { name: 'Add to cart' })`)
3. `getByLabel` for form inputs
4. `getByText` for stable, non-dynamic text

Never use:

- CSS class names that could change with design updates
- `nth-child` or position-based selectors
- DOM depth chains longer than 3 levels

---

## Checkly Config Checklist

For each Checkly check, verify:

- `name` is descriptive
- `url` or script is environment-variable-driven (not hardcoded to production)
- `frequency` is appropriate (critical flows: 5–10 min, smoke: 30–60 min)
- `locations` includes at least two geographic regions
- `alertChannels` are wired to the relevant alert group
- `tags` are set for selective execution

---

## Reliability Checklist

For each Playwright or Checkly test, verify:

- no `waitForTimeout` or fixed sleep calls
- async operations awaited with explicit assertions
- test does not leave side effects (e.g., completed real orders) — use test accounts or draft orders
- credentials are read from environment variables
- failure message is descriptive enough to diagnose without re-running

---

## Output Guidance

When writing an implementation report, include:

1. Flows covered by new or updated tests
2. Selector strategy used
3. Checkly checks added or modified (frequency, locations, tags)
4. Environment variables required
5. Files modified

---

## Avoid

- `waitForTimeout` / `page.waitForTimeout` — use explicit assertions
- Hardcoded URLs, passwords, or API tokens in test files
- Tests that depend on execution order
- Checkly checks that run destructive actions (real checkout completions) without test account isolation
- Duplicate coverage between Playwright unit-style tests and Checkly browser checks
