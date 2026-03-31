# Skill: Shopify Liquid (Online Store 2.0)

Use this skill for:

- implementing or modifying Liquid sections, snippets, and templates
- defining or updating section schema blocks
- working with Shopify global objects (`product`, `cart`, `collection`, `customer`, etc.)
- managing metafields and metaobjects in Liquid
- updating locale translation keys
- layout changes in `theme.liquid` or `password.liquid`

---

## Goals

- Keep Liquid logic minimal and readable
- Prefer OS 2.0 patterns: sections everywhere, blocks, dynamic sources
- Make all merchant-facing content configurable via schema settings
- Keep templates and snippets composable and reusable

---

## Preferred Design

- **Sections** — self-contained blocks with their own schema; used in templates and the editor
- **Snippets** — reusable partials rendered via `render` (never `include`)
- **Templates** — JSON templates for editor compatibility; `.liquid` only when JSON isn't feasible
- **Layout** — only global structure (head, body open/close, cart drawer if global); never section-specific logic

---

## Implementation Rules

1. Every section must have a `{% schema %}` block with at minimum a `name` field
2. Use `render` instead of `include` — `include` is deprecated
3. All merchant-facing text must use locale translation keys (`{{ 'section.key' | t }}`)
4. Access settings via `section.settings.<key>` — never hardcode content
5. Use `content_for_header` and `content_for_layout` in `theme.liquid` — do not remove them
6. Prefer `{{ image | image_url: width: 800 | image_tag }}` over manual `<img>` tags
7. Use `paginate` for collection loops — never output unbounded product lists
8. Access metafields via `product.metafields.namespace.key` — not via `assign` workarounds
9. Use `{% liquid %}` tag for multi-line logic blocks to keep templates readable
10. Avoid Liquid logic in `theme.liquid`; push it into sections or snippets

---

## Section Schema Checklist

For every section, verify:

- `name` is present and human-readable
- `settings` array covers all configurable values (text, image, color, etc.)
- `blocks` are defined if the section supports repeatable content
- `max_blocks` is set when there is a practical upper limit
- `presets` are defined if the section should appear in the theme editor "Add section" list
- `disabled_on` is set if the section should not appear on certain template types

---

## Locale Checklist

- All user-visible strings must have a key in `locales/en.default.json`
- New keys must be placed under a logical namespace (e.g., `sections.hero.heading`)
- Do not duplicate existing keys — check before adding

---

## Output Guidance

When writing an implementation report, include:

1. Sections / snippets / templates added or modified
2. Schema settings added or changed
3. Locale keys added
4. Metafield namespaces used (if any)
5. Files modified

---

## Avoid

- `include` tag (deprecated — use `render`)
- Hardcoded merchant-facing copy in Liquid
- Logic in `theme.liquid` beyond global structure
- Direct HTML `<img>` tags without Shopify image filters
- Unbounded loops over large collections without `paginate`
- Accessing Liquid objects outside their valid scope (e.g., `product` outside a product context)
