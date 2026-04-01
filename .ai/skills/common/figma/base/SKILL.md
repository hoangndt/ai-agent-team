Use Figma MCP whenever the task input includes one or more Figma URLs.

Core expectations:

- Inspect the referenced Figma design before producing the main output.
- Use Figma as an important source of truth for visible UI structure, section hierarchy, labels, and layout intent when available.
- Do not silently guess design details that could be inspected from Figma.
- If Figma inspection fails, is incomplete, or is ambiguous, state that explicitly and continue with best-effort assumptions.

How to use Figma context:

- Focus on the parts of the design that are relevant to the task.
- Summarize key findings instead of dumping raw Figma data.
- Prefer implementation-relevant findings such as sections, components, grouping, labels, form fields, states, layout patterns, and repeated UI blocks.
- If multiple Figma URLs are present, prioritize the one most relevant to the ticket scope.

Output discipline:

- Reference Figma findings only where they materially improve the task output.
- Keep the response/action focused on repository work and ticket scope.
- Do not invent hidden interaction behavior unless it is clearly visible or strongly implied by the design.
