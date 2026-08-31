# ADR-002: Android UI Research Boundary

- Status: Accepted for Phase 0 research only.
- Date: 2026-08-30.
- Class: 4.

## Context

The project contains an Appium and ADB proof of concept for the Garmin Connect Android app. Revision 3 requirements prohibited all interaction with that app. Official Garmin sources reviewed on 2026-08-30 do not affirmatively authorize local accessibility automation and do not clearly decide this exact read-only scenario.

Relevant official sources:

- [Garmin Terms of Use](https://www.garmin.com/en-US/legal/terms-of-use/)
- [Garmin Connect Privacy Policy](https://www.garmin.com/en-US/privacy/connect/policy/)
- [Garmin Developer Programs](https://developer.garmin.com/)

## Decision

Keep the Android probe only as opt-in, local, read-only Phase 0 research:

- Disabled by default.
- Loopback Appium only.
- Exact Garmin Connect package only.
- User-controlled authentication only.
- No Garmin cloud calls.
- No background or unattended operation.
- No screenshots.
- No device or account mutation API.
- Central redaction before all persistence.

Production Android automation or any physical write support requires written Garmin authorization or qualified legal review and a new Class 4 ADR.

## Consequences

The tool can gather sanitized feasibility evidence without claiming Garmin approval. Users must explicitly accept the research boundary for each CLI run or current shell. The project cannot advertise watch optimization or restoration as implemented.
