# Skill: LaunchDarkly Feature Flags

Use this skill for:

- adding or modifying feature flag evaluations
- flag-gated component or route behavior
- flag cleanup (removing deprecated flags)
- flag SDK configuration changes
- reviewing flag usage safety

---

## Goals

- Treat feature flags as first-class, reviewable code
- Never hardcode flag keys as raw strings outside a central location
- Make flag evaluation explicit and traceable
- Ensure fallback behavior is defined for every flag

---

## Design Rules

1. Centralize flag key constants — do not scatter string literals across components
2. Evaluate flags in services, not directly in templates
3. Always define a safe default/fallback value for each flag
4. Do not use flags to control security-sensitive behavior without backend enforcement
5. Keep flag evaluation logic simple — avoid complex boolean combinations where possible
6. Document the intent of each flag at the point of definition

---

## Flag Lifecycle Rules

When adding a flag:

- define the key in a central constants file
- define the expected type and default value
- document when the flag is expected to be cleaned up (short-lived vs long-lived)

When removing a flag:

- ensure the target behavior is now always active
- remove the flag key constant, evaluation call, and any conditional branching
- do not leave dead code behind

---

## Implementation Checklist

For flag-related changes, verify:

- flag key is defined centrally, not inline
- default/fallback value is explicit
- evaluation happens in service layer, not templates
- component receives flag state as a typed input or observable
- both flag-on and flag-off paths are covered in tests
- flag removal leaves no dead code

---

## Output Guidance

When asked to write an implementation report, include:

1. Flag key used
2. Where evaluation happens (service/component)
3. Behavior when flag is on vs off
4. Fallback/default behavior
5. Files modified

---

## Avoid

- inline flag key strings in templates or components
- flag evaluation directly in template expressions
- missing fallback values
- flags that silently default to enabling risky behavior
- leaving cleanup TODOs untracked
