# Skill: Amplitude Analytics

Use this skill for:

- tracking user events with Amplitude
- adding or updating event tracking calls
- session replay configuration
- Amplitude SDK initialization changes
- reviewing analytics coverage gaps

---

## Goals

- Keep analytics tracking calls centralized in a dedicated service
- Do not scatter `amplitude.track()` calls across components
- Make event names and property schemas explicit and consistent
- Do not track PII (personally identifiable information)

---

## SDK Stack

- `@amplitude/analytics-browser` 2.27.0 — core event tracking
- `@amplitude/session-replay-browser` 1.28.21 — session replay
- `@amplitude/plugin-session-replay-browser` 1.22.26 — session replay plugin

---

## Design Rules

1. Initialize Amplitude once in `AppModule` or a root-level service — not per component
2. Wrap all Amplitude calls in an `AnalyticsService` — do not call SDK directly from components
3. Define event name constants in a central file — do not use raw strings in tracking calls
4. Define event property interfaces as typed models
5. Never include PII (user names, emails, patient data) in event properties
6. Session replay must respect user consent settings — check consent state before enabling replay

---

## Event Tracking Checklist

For new or updated tracking events, verify:

- event name is defined in the central constants file
- event properties are typed and documented
- no PII is included in properties
- tracking call is in the service layer, not the component template
- event fires at the correct user action (not on every render)
- event fires once per action, not multiple times (check subscription cleanup)

---

## Session Replay Rules

- Session replay is enabled via `@amplitude/plugin-session-replay-browser`
- Only activate for consented users
- Do not capture sensitive form fields (passwords, PII fields)
- Test replay configuration does not conflict with browser security policies

---

## Output Guidance

When asked to write an implementation report, include:

1. Event name(s) added or modified
2. Event properties tracked
3. Where the tracking call is placed (service/component)
4. Session replay impact (if any)
5. Files modified

---

## Avoid

- Raw `amplitude.track()` calls scattered across components
- Hardcoded event name strings outside the constants file
- Tracking PII in event properties
- Calling Amplitude before SDK initialization is confirmed complete
- Duplicate event fires due to uncleared subscriptions
