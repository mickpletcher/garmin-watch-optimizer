# Changelog

## 2026-08-30

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
