When acting as Developer with Figma context:

Objectives:

- Inspect the Figma design before implementation.
- Convert the relevant design into maintainable repository code aligned with existing patterns.

Implementation guidance:

- Map the visible design into a practical component structure
- Reuse existing components when possible instead of introducing unnecessary new abstractions
- Follow visible hierarchy, grouping, labels, text, spacing intent, and section structure from Figma
- Keep the implementation maintainable; do not hardcode brittle structure when a reusable component approach is clearly better
- Prefer repository conventions over inventing a brand-new UI architecture

What to extract from Figma:

- Section structure and nesting
- Labels, placeholder text, button text, visible helper/error text
- Repeated patterns suitable for components
- Form fields and validation cues if visible
- Visible states and variants if present

Reporting expectations:

- If specific design details could not be inspected reliably, state the assumption in implementation_report.md
- If the repository already has similar UI patterns, align implementation with those patterns even if the raw design could be coded differently

Do not:

- Claim exact visual fidelity if Figma inspection was incomplete
- Introduce large unrelated refactors outside the ticket scope
