# Skill: Tailwind CSS (Shopify Storefront)

Use this skill for:

- styling Shopify theme sections, snippets, and templates with Tailwind
- adding or updating utility classes in Liquid and HTML
- configuring Tailwind (theme extension, custom tokens, purge/content paths)
- replacing custom CSS with equivalent Tailwind utilities
- responsive layout work

---

## Goals

- Use Tailwind utilities as the primary styling mechanism
- Avoid writing custom CSS unless no utility exists for the requirement
- Keep class lists readable and purposeful
- Respect responsive and dark mode breakpoints consistently

---

## Implementation Rules

1. Prefer Tailwind utility classes over `style=""` attributes or custom CSS
2. Keep responsive modifiers consistent: use `sm:`, `md:`, `lg:`, `xl:` in that order
3. Extract repeated class combinations into Liquid snippets or `@apply` groups — not inline duplication
4. Do not use arbitrary values (`w-[123px]`) unless the design token cannot be expressed otherwise
5. Keep `theme/tailwind.config.js` changes minimal — extend `theme.extend`, do not override defaults
6. Content paths in config already include `./assets/*.js`, `./layout/*.liquid`, `./templates/*.liquid`, `./sections/*.liquid`, `./snippets/*.liquid` — do not remove these
7. Use semantic color tokens defined in the config (`charade`, `chambray`, `serenade`, `scarlet`, `pizazz`, etc.) — not raw hex classes
8. Dark mode is configured as `selector` strategy — use `dark:` variants only where the dark mode selector is applied
9. Do not mix Tailwind with a separate CSS framework on the same element
10. Run `npx gulp compile-tailwind` (or `npx gulp`) after config changes to rebuild `assets/tailwind.css`

---

## Responsive Design Checklist

For each UI component, verify:

- mobile-first base styles are set without a breakpoint prefix
- `md:` and `lg:` modifiers adjust layout as screen size increases
- touch targets are at least 44px (use `min-h-11 min-w-11` or equivalent)
- text scales appropriately across breakpoints
- images use responsive width constraints (`w-full max-w-*`)

---

## Tailwind in Liquid Checklist

- Dynamic classes assembled via Liquid string concatenation are **not purged** by Tailwind — use complete class names only
- If a class is conditionally applied, write the full class name in both branches:
  - Correct: `{% if condition %}bg-primary{% else %}bg-surface{% endif %}`
  - Wrong: `bg-{{ condition | if: 'primary', 'surface' }}` (will be purged)
- Add dynamically-generated class names to the Tailwind safelist in config

---

## Output Guidance

When writing an implementation report, include:

1. Components or sections styled
2. Responsive breakpoints addressed
3. Custom config changes (if any)
4. Any classes added to the safelist (if any)
5. Files modified

---

## Avoid

- `style=""` attributes when a Tailwind utility exists
- Arbitrary values for dimensions that should use design tokens
- Duplicate `@apply` blocks that could be a shared snippet instead
- Breakpoint modifiers applied in reverse order (always mobile-first)
- Dynamic class name construction via string interpolation in Liquid
