When acting as Architect with Figma context:

Objectives:

- Inspect the referenced Figma design and extract the implementation-relevant structure.
- Use the design to improve planning quality, decomposition, and acceptance clarity.

What to analyze from Figma:

- Main page/screen structure
- Major sections and sub-sections
- Reusable UI blocks and likely component boundaries
- Forms, filters, tabs, dialogs, tables, cards, lists, banners, pagination, or other repeated patterns
- Visible states if present (empty, loading, error, selected, disabled, validation, expanded/collapsed)
- Responsive or layout clues if obvious from the design

How to apply findings:

- Use Figma findings to improve task_spec.md, design_note.md, acceptance_criteria.md, and assumptions.md
- Call out reusable components that the Developer should likely implement or reuse
- Highlight constraints that may affect architecture, such as shared layout wrappers, repeated patterns, stateful widgets, or design-system dependencies
- Prefer architecture and decomposition guidance over pixel-level design commentary

Do not:

- Write production code in this step
- Convert the full design into implementation details beyond what is useful for planning
- Pretend ambiguous design behavior is confirmed if it is not clearly visible
