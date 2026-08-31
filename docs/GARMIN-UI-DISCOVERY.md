# Garmin UI Discovery Evidence

This file supports `ARCHITECTURE.md`. It is not an architecture authority.

## Selector rules

1. Exact resource identifier when observed and versioned.
2. Exact accessibility description.
3. Exact visible text for the validated locale.
4. No partial text, coordinates, image matching, or generic execute calls in the current probe.

## Parser rules

- A setting requires a clickable node or a setting-specific resource identifier.
- A structured row requires at least a label and a distinct value within the same node subtree.
- Login controls and isolated text nodes are not settings.
- Parsed values pass through redaction before they enter a model.
- Every discovered setting is read only.
- Unknown labels default to high risk.
- Recognized English labels map to stable semantic identifiers such as `system.units` and `power.battery_saver`.
- Unmapped visible rows receive a deterministic `observed.<hash>` identifier and remain high risk unless evidence says otherwise.

## Drift behavior

Unexpected controls, malformed XML, uncertain authentication, missing watch identity, and ambiguous watch selection stop the audit. Diagnostics are optional and sanitized before persistence.

Physical selector evidence remains pending under ISSUE-001.
