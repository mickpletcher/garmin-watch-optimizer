# Agent Rules

## Safety boundary

- Keep the application read only.
- Do not add ADB push, shell mutation, Appium input, tap-by-coordinate, Garmin cloud calls, or watch setting writes.
- `simulate-write-test` must remain in-memory and must not construct ADB or Appium services.
- Block every risk level except explicit `low` in simulation.
- Treat a transport exception after a possible mutation as ambiguous. Journal it, attempt restoration, verify restoration, and fail loudly.
- Stop before Garmin authentication. The user signs in only through Garmin-owned UI.

## Privacy

- Pass every persisted value through `RedactionService`.
- Persist runtime artifacts only under the configured runtime directory.
- Never commit runtime output, device serials, credentials, account data, health data, contacts, Wi-Fi data, or screenshots.
- Keep Appium restricted to loopback addresses.

## Architecture

- CLI and GUI call the same service layer.
- Capability manifests must describe observed evidence and blocked operations accurately.
- Unknown settings default to high risk.
- Exact package identifiers are required. Do not infer Garmin Connect from a package containing `garmin` or `connect`.
- Do not claim hardware acceptance from fake-device tests.

## Validation and documentation

- Follow `PROJECT-STANDARD.md` routing and change classes.
- Add or update tests for each behavioral change.
- Maintain the 85 percent coverage floor for the domain and planning layers.
- Update `CHANGELOG.md`, `VALIDATION.md`, and the relevant authority for Class 3 or Class 4 changes.
- Run `scripts/docs-check.ps1` before committing.
