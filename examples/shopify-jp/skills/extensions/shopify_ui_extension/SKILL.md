# Skill: Shopify UI Extensions

Use this skill for:

- implementing or modifying Shopify UI Extensions (checkout, thank-you page)
- using `@shopify/ui-extensions-react` components
- configuring extension targets in `shopify.extension.toml`
- accessing checkout data via extension APIs (cart lines, buyer identity, attributes)
- rendering conditional UI based on cart state or extension settings

---

## Goals

- Build UI Extensions that are performant within Shopify's sandboxed render environment
- Use only Shopify-approved UI components — never raw HTML or third-party component libraries
- Keep extension logic stateless and reactive where possible
- Declare all extension targets explicitly in TOML

---

## Extension Architecture

Two apps host extensions in this project:

```
apps/
  emma-jp-all-in-one-custom-app/
    extensions/
      additional-delivery-description/
      bundles/
      delivery-customization/
      delivery-disclaimer/
      express-checkout-text/
      free-addon/
      reorder-payment-list/
      schedule-delivery/
      terms-and-conditions-checkbox/
    app/                      # Remix 1.19.0 backend
    prisma/                   # Prisma 5.8.0 session/data storage

  jp-custom-discount-app/
    extensions/
      custom-discount/
      delivery-detail-expand/
      delivery-personal-note/
      [additional checkout extensions]
```

Each extension folder has:

```
<extension-name>/
  src/
    Checkout.tsx              # Primary entry point (TypeScript/TSX)
  shopify.extension.toml     # Target declarations, settings, capabilities
```

- **API version:** `2024-10`
- **Entry point:** `src/Checkout.tsx` registered via `[[extensions.targeting]]` in TOML
- **Components** — from `@shopify/ui-extensions-react/checkout` (e.g., `BlockStack`, `Text`, `Button`, `Banner`, `InlineStack`)
- **Hooks** — from `@shopify/ui-extensions-react` (e.g., `useCartLines`, `useBuyerIdentity`, `useApplyAttributeChange`, `useSettings`, `useTranslate`)
- **Extension targets** — declared in TOML under `[[extensions.targeting]]`

---

## Implementation Rules

1. Do not use `window`, `document`, or any browser globals — the extension runs in a sandbox
2. Do not use `fetch` directly — use Shopify extension API hooks for data access
3. Use only components exported from `@shopify/ui-extensions-react/checkout` or the relevant surface package
4. Declare every used target in `shopify.extension.toml` under `[[extensions.targeting]]`
5. Keep the extension component tree shallow — deeply nested layouts slow render
6. Use `useExtensionCapability` to check for capabilities before calling them
7. All customer-facing text must support localization via the `useTranslate` hook
8. Do not store sensitive data in extension attributes — they are visible in the Shopify admin
9. Settings configured in TOML are accessible via the `useSettings()` hook

---

## TOML Configuration Checklist

Verify that `shopify.extension.toml` includes:

- `api_version = "2024-10"` (project standard)
- `type` set to `ui_extension`
- `name` is human-readable
- `[[extensions.targeting]]` entry for each target the extension renders into
- `module` points to the correct entry file (e.g., `./src/Checkout.tsx`)
- `[[extensions.settings.fields]]` defined for any admin-configurable values

Example TOML:

```toml
api_version = "2024-10"

[[extensions]]
uid = "unique-uid-here"
type = "ui_extension"
name = "My Extension"
handle = "my-extension"

[[extensions.targeting]]
module = "./src/Checkout.tsx"
target = "purchase.checkout.block.render"

[extensions.capabilities]
block_progress = false

[extensions.settings]
[[extensions.settings.fields]]
key = "heading"
type = "single_line_text_field"
```

---

## Supported Targets (Common)

| Target | Surface |
|---|---|
| `purchase.checkout.block.render` | Checkout page (block) |
| `purchase.checkout.cart-line-item.render-after` | After each cart line item |
| `purchase.checkout.shipping-option-list.render-after` | After shipping options |
| `purchase.thank-you.block.render` | Thank-you page |

---

## Output Guidance

When writing an implementation report, include:

1. Which app the extension lives in (`emma-jp-all-in-one-custom-app` or `jp-custom-discount-app`)
2. Extension targets declared and rendered into
3. Shopify API hooks used
4. Components used from `@shopify/ui-extensions-react`
5. Settings fields added to TOML
6. Localization keys added
7. Files modified

---

## Avoid

- Raw HTML elements (`<div>`, `<span>`) — use Shopify UI components
- `fetch` calls — use extension API hooks
- `window` / `document` access
- Third-party UI component libraries
- Storing sensitive customer data in extension attributes
- Targets declared in TOML but not rendered in code (causes validation errors)
- Using a different API version than `2024-10` without explicit instruction
