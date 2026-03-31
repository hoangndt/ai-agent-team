# Skill: JavaScript (Shopify Storefront)

Use this skill for:

- implementing client-side behavior in Shopify themes
- writing or modifying JS source files in `theme/scripts/`
- creating custom HTML elements (web components) with the project's `CustomElement` base class
- AJAX cart interactions (Shopify Cart API)
- pub/sub state management via the project's store pattern
- event handling and DOM manipulation

---

## Architecture

JavaScript source files live in `theme/scripts/` and are compiled by Gulp into `theme/assets/`.

**Two compiled bundles:**
- `assets/core.js` — from `scripts/core/` (in order: `api.js`, `store.js`, `services.js`, `helpers.js`, `resource-coordinator.js`)
- `assets/product.js` — from `scripts/product/` (section-main-product, cross-sell, block-cross-sell-v2, pdp-faq, joint-product-banners)

**This is a Gulp concat pipeline — not an ES module bundler.**
- Do NOT use `import` / `export` statements
- Do NOT use `type="module"` script tags
- All classes and helpers defined in earlier files in the bundle are available to later files as globals

**jQuery 3.6.0** is loaded globally. Use `$` / `jQuery` freely inside custom elements.

---

## Custom Element Pattern

All interactive UI components are **custom HTML elements** extending the `CustomElement` base class defined in `scripts/core/helpers.js`.

### Base classes available

```js
// CustomElement — base for all components
class CustomElement extends HTMLElement {
  props = null               // declare as object with defaults; populated by extractProps()
  $el                        // jQuery wrapper set in constructor: this.$el = $(this)

  // Lifecycle (called automatically):
  // setup()          → called in constructor; set up MutationObserver, etc.
  // connectedCallback() → extractProps() → init() → beforeMount() → render() → mounted()
  // disconnectedCallback() → onDestroy()

  // Override these hooks:
  setup() {}
  init() {}
  beforeMount() {}
  render() {}          // default: sets this.innerHTML = this.template() if template() returns a value
  template() {}        // return HTML string to replace inner content
  mounted() {}
  onDestroy() {}
  onMutation() {}
  onValueChange(newVal) {}
}

// CustomButton — extends CustomElement, handles click with disabled/readOnly guards
class CustomButton extends CustomElement {}
```

### Creating a new custom element

1. Create a class extending `CustomElement` (or `CustomButton`)
2. Declare `props` as an object with default values — they will be populated from `:propName` attributes
3. Register with `customElements.define('tag-name', ClassName)`
4. Add the source file to the correct Gulp bundle (`scripts/core/` or `scripts/product/`)
5. Use the custom tag in Liquid: `<tag-name :propName="{{ data | json | escape }}"></tag-name>`

```js
class BlockMyFeature extends CustomElement {
  props = {
    product: null,
    label: 'Add',
  }

  init() {
    super.init()
    // this.props.product and this.props.label are available here
  }

  mounted() {
    this.$el.find('[data-action]').on('click', this.handleClick.bind(this))
  }

  handleClick(event) {
    // cart interactions, state updates, etc.
  }

  onDestroy() {
    // clean up listeners if needed
  }
}

customElements.define('block-my-feature', BlockMyFeature)
```

### Prop passing from Liquid

Props are passed as `:propName` attributes with JSON-encoded values. `extractProps()` reads each entry in `this.props`, looks up `:propname` (lowercased), and attempts `JSON.parse`.

```liquid
<block-my-feature
  :product="{{ product | json | escape }}"
  :label="{{ 'section.add_to_cart' | t | json }}"
></block-my-feature>
```

---

## State Management

The project uses a pub/sub store pattern. `ProductPageStore` (from `scripts/core/store.js`) is the main state bus on the product page.

```js
// Subscribe
ProductPageStore.subscribe('eventName', (data) => { /* handler */ })

// Publish
ProductPageStore.publish('eventName', { key: value })
```

Use this for cross-component communication rather than DOM traversal or global variables.

---

## Cart API

Use `fetch` with Shopify's AJAX Cart API:

```js
// Add to cart
fetch('/cart/add.js', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ id: variantId, quantity: 1 }),
})

// Update quantity
fetch('/cart/change.js', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ id: variantId, quantity: newQty }),
})

// Get cart
fetch('/cart.js').then(r => r.json())
```

Always handle errors explicitly — surface them to the user, do not swallow rejected promises.

---

## Implementation Rules

1. Use `const` and `let` — never `var`
2. New components → extend `CustomElement` or `CustomButton`, register with `customElements.define()`
3. Props go in `this.props = { key: default }`, populated automatically by `extractProps()`
4. Use `this.$el` (jQuery) for DOM queries within the component
5. Use `data-*` attributes for DOM targeting — not CSS class names
6. Cross-component communication → pub/sub via `ProductPageStore`, not DOM traversal
7. Debounce scroll and resize listeners
8. Always handle fetch errors explicitly
9. Do NOT use `import` / `export` — this is a concat build, not a module bundler
10. Do NOT use `type="module"` script tags in Liquid
11. Use `Shopify.routes.root` for correct URL construction in non-root deployments

---

## Build Workflow

```bash
cd theme

# Compile all (CSS + JS) + watch JS:
npx gulp

# Compile and watch CSS only:
npx gulp watch:css

# Compile JS bundles once:
npx gulp compile-core
npx gulp compile-product
```

After adding a new source file, add it to the correct `src` array in `gulpfile.js` — order matters.

---

## Output Guidance

When writing an implementation report, include:

1. Class name, tag name, and which bundle it belongs to (`core` or `product`)
2. Props declared and their types
3. Lifecycle hooks used
4. Cart API or store events used (if any)
5. Liquid usage (how the tag is placed in a section/snippet)
6. Files modified

---

## Avoid

- `var` declarations
- `import` / `export` ES module syntax
- `type="module"` script attributes
- Global variable assignments on `window` (except for intentional global stores)
- Inline `onclick` / `onsubmit` HTML attributes
- `document.write`
- Uncaught promise rejections
- Hardcoded store URLs — use `Shopify.routes.root` or relative paths
- Writing logic directly in `<script>` tags inside Liquid sections — use custom elements instead
