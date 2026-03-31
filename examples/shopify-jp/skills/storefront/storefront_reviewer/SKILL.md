# Skill: Shopify Storefront Reviewer

Use this skill for:

- reviewing changes to Liquid sections, snippets, templates, and layout
- reviewing Tailwind CSS usage in theme files
- reviewing JavaScript modules in `theme/assets/`
- validating section schema completeness and correctness
- checking locale key coverage

---

## Review Priorities

Review in this order:

1. correctness — does the Liquid render correctly without errors?
2. schema completeness — are all merchant-configurable values in the schema?
3. locale coverage — are all user-visible strings using translation keys?
4. JavaScript safety — no global pollution, no deprecated APIs
5. Tailwind usage — utilities used correctly, no dynamic class interpolation
6. acceptance criteria fit — does the change address the ticket's stated goal?
7. maintainability — is the change minimal, localized, and consistent with existing patterns?

---

## Review Checklist

### Liquid

- does the section have a complete `{% schema %}` block with a `name` field?
- are all merchant-facing strings using `{{ 'key' | t }}` locale references?
- is `render` used instead of `include`?
- are images using Shopify image filters (`image_url`, `image_tag`)?
- are collections and product lists paginated where appropriate?
- are metafields accessed via `metafields.namespace.key` (not `assign` hacks)?
- does the section work in the theme editor (responds to `shopify:section:load`)?

### Schema

- does every configurable value have a corresponding setting in the schema?
- are setting types correct (`text`, `image_picker`, `color`, `richtext`, etc.)?
- are `presets` defined if the section should appear in "Add section"?
- are `disabled_on` constraints applied where needed?

### Tailwind

- are utility classes used instead of `style=""` or custom CSS?
- are dynamic class names written as full strings (not interpolated)?
- are responsive modifiers applied mobile-first?

### JavaScript

- no `var` declarations?
- no `window` assignments (except intentional global stores)?
- no inline event handlers (`onclick=""`, `onsubmit=""`)?
- no `import` / `export` or `type="module"` — Gulp concat pipeline only?
- new components extend `CustomElement` or `CustomButton` from `scripts/core/helpers.js`?
- `customElements.define('tag-name', ClassName)` called for each new element?
- props declared in `this.props = {}` and passed via `:propName` attributes in Liquid?
- are cart/section API calls using correct Shopify endpoints?
- are fetch errors handled explicitly?
- new source files added to the correct Gulp bundle in `gulpfile.js`?

---

## Decision Guidance

- approve:
  - schema is complete, locale keys are present, Liquid is correct
  - no meaningful JS or Tailwind issues
- request_changes:
  - missing schema settings, hardcoded copy, deprecated tags, unsafe JS patterns
- block:
  - Liquid syntax errors or logic that would break section rendering
  - missing `content_for_layout` or `content_for_header` in layout
  - JS that pollutes global scope or causes cart API data corruption

---

## Avoid

- approving sections with hardcoded merchant copy
- ignoring missing locale keys as a minor style issue — they break translation
- approving dynamic Tailwind class interpolation (classes will be purged)
- treating missing schema settings as low priority — they break merchant customization
