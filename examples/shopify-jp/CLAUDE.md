# Shopify Stores AI Workflow Guide

This repository contains a Shopify storefront with custom theme, extensions, and E2E tests:

- `theme/` — Shopify Online Store 2.0 theme (Liquid, Tailwind CSS, Vanilla JS custom elements, SCSS)
- `apps/` — Two Shopify custom apps with Checkout UI Extensions and Shopify Functions
  - `apps/emma-jp-all-in-one-custom-app/` — Remix-based app with 9 checkout UI extensions
  - `apps/jp-custom-discount-app/` — Discount-focused app with functions and UI extensions
- `e2e/` — Playwright + Checkly end-to-end tests

Current AI workflow default domain is **storefront**.
Unless explicitly asked otherwise, prioritize storefront-related tasks.

---

## Working Model

Use the structured workflow in `.ai/runs/<TICKET>/`.

Typical stages:

1. Architect
2. Developer
3. Reviewer
4. QA

Read and write workflow artifacts inside `.ai/runs/<TICKET>/`.

---

## Repository Priorities

For now, prefer work inside:

- `theme/`

Do not modify `apps/` or `e2e/` unless:

- the task explicitly requires it
- or the storefront change has a direct extension or test dependency

---

## Storefront Stack (`theme/`)

Primary technologies:

- Shopify Liquid (Online Store 2.0)
- Tailwind CSS 3.3.1 (JIT, configured via `theme/tailwind.config.js`)
- SCSS 1.89.2 (source in `theme/styles/`, compiled via Gulp)
- Vanilla JavaScript ES6+ — **custom HTML elements** extending the `CustomElement` base class
- jQuery 3.6.0 (global `$`, available in all custom elements)
- Gulp 4 build pipeline (concatenation + Terser minification)
- pnpm 10 as package manager

Theme directory structure:

```
theme/
  assets/          # Compiled output: core.js, product.js, tailwind.css, base.css, global.css, fonts, images
  config/          # settings_schema.json, settings_data.json
  layout/          # theme.liquid
  locales/         # translation JSON files (ja.default.json, en.json, etc.)
  scripts/         # JavaScript source files (NOT deployed directly)
    core/          # api.js, store.js, services.js, helpers.js, resource-coordinator.js → compiled to assets/core.js
    product/       # section-main-product.js, cross-sell.js, block-cross-sell-v2.js, etc. → compiled to assets/product.js
  sections/        # Liquid sections with {% schema %} blocks
  snippets/        # Reusable Liquid partials
  styles/          # SCSS source files → compiled to assets/
    tailwind.scss  # Entry point for Tailwind + SCSS pipeline
  templates/       # Page templates
  gulpfile.js      # Build tasks: compile-tailwind, compile-core, compile-product, watch-js, watch:css
  tailwind.config.js
```

**Build pipeline:**
- CSS: `styles/tailwind.scss` → SASS → Tailwind PostCSS → CSSNano → `assets/tailwind.css`
- JS: `scripts/core/*.js` → concat → Terser → `assets/core.js`
- JS: `scripts/product/*.js` → concat → Terser → `assets/product.js`
- Run: `cd theme && npx gulp` (default task compiles all + watches JS)

When implementing or reviewing storefront work:

- prefer Online Store 2.0 patterns: sections, blocks, metafields
- JavaScript behavior belongs in a **custom HTML element** class, not an inline `<script>` tag
- use Tailwind utility classes; write custom SCSS only for cases utilities cannot cover
- all merchant-facing text must use `t:` translation keys
- respect section schema for all merchant-configurable values — never hardcode content
- use `{{ 'file.js' | asset_url }}` for asset references; `{{ 'file.js' | asset_url | script_tag }}` is acceptable shorthand
- do NOT use ES module `type="module"` scripts — the build is a Gulp concat pipeline, not a module bundler

---

## Extensions Stack (`apps/`)

Primary technologies:

- Shopify UI Extensions — TypeScript/TSX with `@shopify/ui-extensions` and `@shopify/ui-extensions-react`
- Shopify Functions — JavaScript (via `@shopify/shopify_function`)
- Remix 1.19.0 backend (emma-jp-all-in-one-custom-app only)
- Prisma 5.8.0 for database (emma-jp-all-in-one-custom-app only)
- Shopify CLI (`shopify app dev`, `shopify app deploy`)
- API version: `2024-10`

Extension structure:

```
apps/
  emma-jp-all-in-one-custom-app/
    extensions/
      <extension-name>/
        src/
          Checkout.tsx        # UI Extension entry point
        shopify.extension.toml
    app/                      # Remix backend routes
    prisma/                   # DB schema and migrations
  jp-custom-discount-app/
    extensions/
      <extension-name>/
        src/
          Checkout.tsx
        shopify.extension.toml
```

When implementing or reviewing extensions work:

- use Shopify's built-in UI components from `@shopify/ui-extensions-react/checkout`
- keep UI Extensions stateless where possible; use extension API hooks for data access
- Shopify Functions must be pure: same inputs produce same outputs, no side effects
- test Functions locally with `shopify app function run` before marking complete
- extension targets must match what is declared in `shopify.extension.toml`

---

## E2E Stack (`e2e/`)

Primary technologies:

- Playwright 1.58.2 (TypeScript, Chromium only)
- Checkly monitoring-as-code (`@checkly/cli`)
- Page Object Model pattern
- dotenv for environment configuration

Structure:

```
e2e/src/
  __checks__/    # Checkly browser checks (*.check.ts)
  components/    # Reusable test component helpers
  fixtures/      # Test data fixtures
  pages/         # Page Object Model classes
  tests/         # Playwright test specs
  utils/         # Environment helpers
```

When implementing or reviewing E2E work:

- cover critical customer journeys: product discovery, cart, checkout, account
- use `data-testid` attributes as the primary selector strategy
- Checkly checks run on a schedule (every 60 min, US East 1 + EU Central 1) — keep them lightweight
- never hardcode passwords or tokens in test files; use environment variables
- separate Playwright local tests (`src/tests/`) from Checkly monitors (`src/__checks__/`)

---

## General Rules

1. Stay within ticket scope
2. Prefer existing patterns over new abstractions
3. Read files directly from the repository
4. Write required outputs directly to target files
5. Be explicit about assumptions and unknowns
6. Do not invent requirements
7. Keep output structured and concise

---

## Storefront-Specific Rules

- All sections must define a `{% schema %}` block with at minimum a `name` field
- Merchant-facing copy must never be hardcoded — use locale keys
- Do not use deprecated Liquid filters or tags (e.g., `include` → use `render`)
- Tailwind: do not add arbitrary `style=""` attributes when a utility class exists
- JavaScript: write custom elements extending `CustomElement` or `CustomButton` from `scripts/core/helpers.js`
- Pass data to custom elements via `:propName` attributes (JSON-encoded), read in `extractProps()`
- Use `this.$el` (jQuery wrapper) for DOM manipulation within custom elements
- Never use `type="module"` scripts — Gulp concat pipeline does not support ES module imports
- Source files go in `theme/scripts/core/` or `theme/scripts/product/`; compiled output lands in `theme/assets/`
- Keep `theme.liquid` lean — do not add per-section logic to the layout file
- Metafields should be accessed via `metafields` object, not liquid `assign` hacks

---

## Extensions-Specific Rules

- UI Extensions run in a sandboxed iframe — no access to `window`, `document`, or global DOM
- Do not use `fetch` directly in UI Extensions; use extension API hooks
- Shopify Functions have strict execution time limits (5ms) — keep logic fast and pure
- Every TOML extension target must be tested against a real checkout flow before approval
- Entry file is typically `src/Checkout.tsx`; confirm with `shopify.extension.toml`

---

## E2E-Specific Rules

- Playwright tests must not depend on test execution order
- Use `test.describe` to group related flows
- Checkly checks must use environment variables for store URL, credentials, and API tokens
- Tag slow or destructive tests so they can be excluded from local runs

---

## Output Rules by Role

### Architect

- define scope clearly
- identify affected theme files (sections, snippets, templates, scripts, styles)
- clarify Liquid schema, locale, and metafield implications
- identify extension targets or Function inputs/outputs if relevant
- do not write code

### Developer

- implement minimal correct solution
- localize changes to the relevant domain directories
- for storefront JS: add a new class extending `CustomElement` or `CustomButton`; register with `customElements.define()`
- keep the implementation report factual and include commands run

### Reviewer

- focus on Liquid correctness, schema completeness, Tailwind usage, JS safety
- check locale key coverage and schema field completeness
- verify custom elements: register name matches tag in Liquid, props are extracted correctly
- for extensions: verify target declarations, component API usage, and Function purity
- for E2E: verify selector strategy, test isolation, and Checkly config correctness

### QA

- focus on missing customer journey coverage, edge cases, and regression risk
- validate that schema changes don't break existing merchant settings
- for extensions: verify all extension targets are exercised in test scenarios
- for E2E: verify Checkly monitor coverage matches critical business flows

---

## Success Criteria

A task is successful when:

- required files are created correctly
- Liquid sections have complete schema blocks
- all merchant-facing text uses locale keys
- Tailwind classes are used instead of custom CSS where possible
- JavaScript custom elements are properly registered and extend `CustomElement`
- extensions run within Shopify's sandbox constraints
- E2E tests cover the stated acceptance criteria with stable selectors
- the next agent can continue without ambiguity
