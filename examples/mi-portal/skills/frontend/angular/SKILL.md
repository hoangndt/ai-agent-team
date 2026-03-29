# Skill: Angular Frontend

Use this skill for:

- component implementation
- service and state management changes
- module structure changes
- routing changes
- template and reactive form updates
- Angular-specific refactors

---

## Goals

- Keep components small and focused on a single responsibility
- Put business logic in services, not templates or components
- Prefer reactive patterns (RxJS, signals) consistent with the codebase
- Reuse existing module structure
- Avoid unnecessary abstractions

---

## Preferred Design

- Component layer:
  - template rendering
  - user interaction wiring
  - delegates to services for all data/business logic
- Service layer:
  - HTTP calls
  - business rules
  - state management
- Module/feature layer:
  - lazy-loaded feature modules where applicable
  - shared module for cross-cutting concerns

---

## Implementation Rules

1. Prefer existing module and file structure in `frontend/`
2. Do not create new modules unless the task clearly requires it
3. Keep templates lean — avoid logic beyond simple conditionals
4. Unsubscribe from observables correctly (async pipe preferred)
5. Handle all three loading states: loading, error, empty
6. Do not inline HTTP calls in components
7. Keep routing changes minimal and scoped to the task

---

## Component Checklist

When implementing or reviewing a component, check:

- single responsibility respected
- template is readable and not bloated
- inputs/outputs are clearly typed
- loading / error / empty states handled
- subscriptions cleaned up
- no direct HTTP calls in component
- service dependencies are injected, not instantiated

---

## Output Guidance

When asked to write an implementation report, include:

1. Component(s) added or modified
2. Service(s) added or modified
3. Key behavior added/changed
4. State/loading handling
5. Files modified

---

## Avoid

- fat components
- logic in templates beyond simple bindings
- manual subscriptions without cleanup
- direct DOM manipulation
- broad refactors outside scope
