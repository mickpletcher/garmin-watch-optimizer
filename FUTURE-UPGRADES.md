# Future Upgrades

## Phase 0 research

- Validate the read-only Android probe on a physical Enduro 2 with sanitized evidence.
- Inventory Garmin Express controls on current Windows and macOS releases.
- Map supported USB/MTP artifacts without writing to the device.
- Document native Garmin backup coverage and recovery limits.
- Request written Garmin guidance for local Android accessibility automation.

## Phase 1 configuration engine

- Versioned YAML schema and generated JSON Schema.
- Capture bundles with checksums and explicit captured, partial, unavailable, and excluded states.
- Bundle-to-bundle comparison.
- Desired-state diff, dry-run plan, overlays, dependency ordering, and job journals.
- Fake adapters for disconnect, partial failure, resume, rollback, and idempotency.

## Later phases

- Guided on-watch actions.
- Activity favorites and ordering workflow.
- Garmin Express adapter only where supported and authorized.
- Signed installers, SBOM, dependency audit, release signing, and update policy.
- Additional first-party watch capability profiles.
- Third-party plugins only after sandboxing, permissions, signing, and trust contracts exist.
