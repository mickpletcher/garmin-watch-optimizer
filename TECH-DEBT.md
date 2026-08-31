# Technical Debt

## TD-001: CLI framework

The current CLI uses `argparse`. The product requirements propose a typed scripting surface, structured JSON output, and non-interactive modes. Revisit after the configuration engine exists.

## TD-002: Page object versioning

Semantic selectors are centralized but are not yet versioned by Garmin Connect release or locale. Physical evidence is required before creating compatibility profiles.

## TD-003: Packaging and dependency lock

Development dependencies use bounded minimum versions without a lock file. Add reproducible release locking, signed installers, SBOM generation, and dependency audit before the first release.

## TD-004: GUI automation evidence

GUI behavior is not covered by UI-level tests. Service behavior is covered independently. Add Qt interaction tests after the workflow stabilizes.
