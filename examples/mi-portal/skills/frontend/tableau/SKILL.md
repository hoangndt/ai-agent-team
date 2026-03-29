# Skill: Tableau Embedded Reports

Use this skill for:

- embedding Tableau views or dashboards in Angular components
- Tableau embed configuration changes
- filter/parameter passing to embedded views
- handling Tableau load states and errors
- Tableau token/authentication flow changes

---

## Goals

- Keep Tableau embed logic isolated from business components
- Handle embed lifecycle states explicitly (loading, loaded, error)
- Make filter/parameter passing traceable and centralized
- Do not leak Tableau SDK internals into unrelated modules

---

## Design Rules

1. Wrap Tableau embed logic in a dedicated service or component
2. Do not instantiate Tableau viz objects directly in feature components
3. Pass filters/parameters through a clear, typed interface
4. Handle load events explicitly — do not assume the viz is ready immediately
5. Handle error states — Tableau embeds can fail silently
6. Keep embed URLs and site configuration in a central config location

---

## Embed Lifecycle Checklist

For any Tableau embed implementation, verify:

- loading state is shown while viz initializes
- error state is handled if embed fails to load
- viz is properly disposed/destroyed on component teardown
- filter and parameter passing is tested with known values
- embed does not block page interaction during load

---

## Filter/Parameter Rules

- Define filter interfaces as typed models, not raw string maps
- Validate filter values before passing to Tableau
- Do not construct Tableau filter objects inline in templates
- Log filter application for observability

---

## Authentication/Token Rules

- Tableau connected app or trusted token logic must be server-side
- Do not expose Tableau credentials or tokens in frontend code
- If token refresh is needed, handle it in the service layer

---

## Output Guidance

When asked to write an implementation report, include:

1. Tableau view or workbook targeted
2. Embed configuration changes
3. Filters/parameters passed
4. Load and error state handling
5. Files modified

---

## Avoid

- Tableau SDK calls scattered across unrelated components
- assuming the viz is ready without waiting for load events
- exposing Tableau site credentials in frontend config
- hardcoding Tableau view URLs outside a config location
