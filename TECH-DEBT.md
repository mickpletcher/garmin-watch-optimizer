# Technical Debt

## TD-001: CLI framework

The current CLI uses `argparse`. Offline commands now share the domain services, but output is not uniformly selectable between human-readable and JSON modes. Add a consistent `--json` contract and non-interactive exit-code table before packaging.

## TD-002: Page object versioning

Semantic selectors are centralized but are not yet versioned by Garmin Connect release or locale. Physical evidence is required before creating compatibility profiles.

## TD-003: Packaging and dependency lock

Dependencies use bounded ranges without a release lock file. CI now audits dependencies and produces a CycloneDX SBOM. Add reproducible release locking, signed installers, and installer provenance before the first release.

## TD-004: GUI automation evidence

GUI behavior is not covered by UI-level tests. Service behavior is covered independently. Add Qt interaction tests after the workflow stabilizes.
