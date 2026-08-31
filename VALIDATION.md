# Validation

## Automated acceptance

Run from the repository root:

```powershell
python -m pytest
python -m ruff check .
python -m mypy src
python -m pip check
python -m pip_audit --skip-editable
python scripts/generate_schema.py
git diff --exit-code -- schemas/config.schema.json
./scripts/docs-check.ps1
```

Required outcomes:

- All non-hardware tests pass.
- The opt-in hardware test is skipped unless explicitly enabled.
- Domain and planning layer coverage is at least 85 percent.
- Ruff and Mypy report no errors.
- Installed dependencies have no broken requirements.
- Every Tier 2 authority resolves.
- The committed JSON Schema matches the generated Pydantic model.
- Installed dependencies have no known published vulnerability in the audit database.

## Current evidence

Validated on 2026-08-30:

- Python test suite: 58 passed, 1 hardware test skipped.
- Domain and planning coverage: 93 percent.
- Ruff: passed.
- Mypy: passed across 28 source files.
- Fake-device contract: passed through exact app selection, authentication, navigation, Enduro 2 identity, firmware, settings capture, capability manifest, and session cleanup.
- Failure injection: destructive and all other non-low risks blocked; ambiguous mutation restored and journaled; verification failure restored; restoration failure persisted and failed loudly; journal failure blocked before simulated mutation.
- Privacy tests: device identifiers, email, phone, token-like values, passwords, and sensitive setting values are removed from persisted artifacts.
- Configuration tests: strict YAML and JSON loading, deterministic overlays, conflict reporting, schema drift detection, sensitive-input blocking, and idempotency properties passed.
- Bundle tests: coverage records, checksum verification, tamper detection, safe ZIP round trip, path traversal blocking, compression-bomb blocking, and summary redaction passed.
- Bundle failure injection: a manifest persistence failure removed the temporary directory and left no partial bundle.
- Planning tests: already-compliant, guided, unsupported, unknown, strict-removal, cross-model, and firmware-incompatibility paths passed with zero automatic operations.
- Offline CLI contract: capture, validation, overlay planning, and ZIP export completed without constructing ADB or Appium services.
- Local dependency audit: no known vulnerabilities found; the editable project itself is excluded because it is not a published PyPI distribution.
- GitHub evidence: PR #2 passed Python 3.12 and 3.13 on Windows and macOS, CodeQL, dependency review, dependency audit, and CycloneDX SBOM generation. The dependency audit found no known vulnerabilities.

## Hardware gate

The hardware test is read only and must be explicitly enabled:

```powershell
$env:GARMIN_OPT_HARDWARE_TESTS = "1"
python -m pytest -m hardware --no-cov
```

Hardware acceptance remains pending. Passing the fake-device contract does not satisfy it.

## Physical write gate

No physical write command or adapter exists. Do not add one until all Section 5.1 and Phase 0 gates in `REQUIREMENTS.md` are satisfied and recorded in a Class 4 ADR.
