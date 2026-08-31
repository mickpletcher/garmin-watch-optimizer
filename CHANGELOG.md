# Changelog

## 0.3.0 - 2026-08-30

- Added strict YAML and JSON desired-state models, generated schema drift enforcement, safe parsing, and sensitive-input blocking.
- Added deterministic ordered overlays with conflict reporting.
- Added sanitized configuration capture bundles with explicit coverage states and SHA-256 integrity validation.
- Added secure ZIP import and export with path, link, size, compression-ratio, payload, and checksum defenses.
- Added read-only bundle comparison and snapshot planning with model and firmware compatibility gates and zero automatic operations.
- Added ADR-003 for the offline configuration and archive trust boundary.
- Added stable semantic identifiers for recognized settings and deterministic hashes for unmapped visible rows.
- Expanded capability manifests with explicit read and write support, adapter, transport, constraints, side effects, rollback, risk, and evidence.
- Added offline CLI capture, validate, compare, plan, bundle import, and bundle export commands that do not construct device transports.
- Added property-based idempotency tests, malicious-input tests, schema golden tests, and offline transport-isolation tests.
- Expanded CI to Python 3.12 and 3.13 on Windows and macOS, pinned Actions, and added dependency review, vulnerability auditing, and CycloneDX SBOM generation.
- Protected `main` with administrator-enforced pull requests, strict validation gates, linear history, blocked force pushes and deletion, squash-only merges, and automatic branch cleanup.
- Enabled read-only Actions defaults, secret scanning with push protection, Dependabot alerts, security update pull requests, and monthly dependency updates.
- Added requirement traceability and reconciled all Tier 2 authorities with the implemented scope.

## 0.2.0 - 2026-08-30

- Reconciled local history with the remote requirements commit and promoted the newer Revision 3 additions into Revision 4.
- Resolved Garmin Connect Android automation as disabled-by-default, opt-in, local, read-only research with no claim of Garmin authorization.
- Removed the physical ADB write primitive and replaced `write-test` with transport-free `simulate-write-test`.
- Added typed fail-closed risk levels, durable simulation journals, ambiguous failure handling, restoration attempts, and restoration verification.
- Added exact Garmin Connect package validation, explicit serial validation, authentication detection, Enduro 2 selection, firmware discovery, semantic navigation, capability manifests, and session cleanup.
- Centralized redaction and atomic persistence for snapshots, reports, manifests, diagnostics, journals, and logs.
- Added fake-device contract tests, failure injection, a read-only hardware smoke gate, and an enforced 85 percent domain-layer coverage floor.
- Added Windows and macOS CI, CodeQL, and Dependabot configuration.
- Added Tier 2 authority mapping, governance, architecture, security, research, compatibility, operations, validation, issue, debt, and future-work documentation.

## 2026-08-28

- Bootstrapped the Garmin Watch Optimizer Python proof of concept.
