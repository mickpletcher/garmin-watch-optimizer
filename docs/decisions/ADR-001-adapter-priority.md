# ADR-001: Adapter Priority

- Status: Accepted.
- Date: 2026-08-30.
- Class: 4.

## Context

Garmin does not expose one documented interface for every Enduro 2 setting. Candidate transports have different authorization, safety, recovery, and compatibility properties.

## Decision

Production capability research follows this priority:

1. Documented Garmin interface or file format.
2. Supported device storage access with copy-first parsing and atomic replacement only where documented.
3. Confirmed Garmin Express controls through platform accessibility APIs.
4. Guided user action.
5. Read-only reporting.

Unknown firmware and undocumented write mechanisms remain read only. The Android UI research probe is not a production adapter and is governed separately by ADR-002.

## Consequences

The application may report many settings as unsupported or guided. That is preferable to guessing. A lower-priority transport cannot silently override the absence of a higher-priority safe capability.
