# Adapter Boundaries

## Adapter priority

Use the safest available surface in this order:

1. Documented Garmin interface or file format.
2. Supported device storage access with copy-first parsing.
3. Confirmed Garmin Express control through platform accessibility APIs.
4. Guided user action.
5. Read-only reporting.

The Garmin Connect Android research probe is outside the production adapter priority. It exists only to gather Phase 0 read-only evidence under ADR-002.

## Current implementations

### Android UI research probe

- Status: Implemented for fake-device contract testing. Physical acceptance pending.
- Access: Read only.
- Default: Disabled.
- Transport: Loopback Appium plus ADB read operations.
- Authentication: User controlled. Sign-in screens stop the audit.
- Output: Sanitized snapshot, capability manifest, diagnostics, and reports.
- Writes: Unavailable.

### Simulation adapter

- Status: Implemented.
- Access: Process memory only.
- Purpose: Validate risk gates, journaling, ambiguous failure handling, verification, and restoration.
- Device dependencies: None.
- Writes: Cannot reach Android, Garmin Connect, Garmin cloud, or a watch.

## Planned production contract

Future production adapters must expose explicit capability methods rather than a generic command channel:

```text
probe(context) -> capability manifest
capture(capability) -> typed observed state
plan(current, desired) -> operations
backup(operations) -> recovery artifact
apply(operation) -> attempt result
verify(operation) -> independently read result
rollback(operation, recovery artifact) -> recovery result
```

An adapter must declare supported models, firmware ranges, transport, risk, recovery coverage, side effects, verification method, and evidence. Unknown firmware defaults to read only. Generic ADB shell, Appium execute, arbitrary file push, coordinate tapping, and stored credential entry are prohibited.
