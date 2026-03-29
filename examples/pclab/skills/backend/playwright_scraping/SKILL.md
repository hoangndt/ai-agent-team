# Skill: Playwright Scraping / Browser Automation

Use this skill for:

- scraping dynamic sites
- search/result extraction
- browser-based enrichment flows
- fallback fetching with browser automation
- resilient selector handling

---

## Goals

- Build reliable browser automation
- Minimize flaky behavior
- Prefer deterministic extraction logic
- Separate browser concerns from business logic
- Make failures observable

---

## Design Rules

1. Keep Playwright code isolated in dedicated provider/client modules
2. Do not scatter browser startup logic across unrelated modules
3. Prefer a controlled browser lifecycle
4. Use explicit waits tied to stable page state
5. Handle cookie banners or modal interruptions defensively
6. Capture partial failure cleanly
7. Return structured data, not raw browser artifacts unless required

---

## Selector Rules

Prefer:

- semantic selectors
- stable attributes
- narrowly scoped DOM queries

Avoid:

- brittle nth-child selectors
- selectors tied to cosmetic layout
- unnecessary long chains

---

## Reliability Checklist

For scraping/enrichment code, verify:

- page load/wait strategy is explicit
- transient errors are retried where appropriate
- selectors have fallback strategy if needed
- empty result behavior is defined
- partial extraction behavior is defined
- timeout behavior is defined
- logging explains which step failed
- browser/session cleanup is handled

---

## Fallback Strategy

When both non-browser and browser fetch methods exist:

- prefer lightweight fetch first if reliable
- use Playwright fallback when dynamic rendering blocks extraction
- log fallback usage clearly

---

## Output Guidance

Implementation or review notes should mention:

- how search pages are loaded
- how results are selected/scored
- how target pages are fetched
- how structured fields are extracted
- how transient failures, retries, and fallbacks behave

---

## Avoid

- mixing scraping logic into API routers
- hiding retries in too many layers
- treating unstable DOM assumptions as guaranteed truth
- returning success when extraction is clearly incomplete unless partial results are intentional
