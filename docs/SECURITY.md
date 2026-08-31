# Security and Privacy

## Decision

The supported system is local and read only. Android UI research is disabled by default. There is no physical write adapter.

Official Garmin sources reviewed on 2026-08-30 did not affirmatively authorize local Android accessibility automation. Garmin's Terms of Use prohibit automated access to Garmin Site content through methods Garmin did not purposely provide and restrict exploitation or reverse engineering of downloaded software. Those terms do not clearly decide this exact local read-only app scenario. See ADR-002.

Untrusted configuration and archive handling is governed by ADR-003.

This is a conservative engineering policy, not legal advice.

## Protected assets

- Garmin account session and credentials.
- Android device identifiers.
- Watch identity and firmware.
- Activity, health, wellness, location, contact, payment, network, and safety data.
- UI hierarchy diagnostics.
- Local snapshots, reports, manifests, journals, and logs.

## Threats and controls

| Threat | Control |
| --- | --- |
| Wrong Garmin app selected | Exact package allowlist. Connect IQ is rejected. |
| Wrong Android device selected | Explicit serial validation or a single authorized-device requirement. |
| Remote Appium access | Loopback hostname allowlist. |
| Credential capture | Sign-in detection stops navigation. No text-entry API. |
| Garmin cloud scraping | No HTTP client for Garmin endpoints. Appium is local only. |
| UI drift causing unintended action | Exact semantic selectors and fail-closed navigation. No coordinate clicks. |
| Personal data persisted | One recursive redaction service for snapshots, manifests, reports, diagnostics, journals, and logs. |
| Partial or ambiguous write | No physical write path. Simulation journals before change and restores on ambiguity. |
| Destructive setting accepted | Typed risk enum. Simulation accepts only explicit low risk. Unknown defaults to high. |
| Artifact corruption or collision | Unique microsecond filenames and atomic same-directory replacement. |
| Accidental publication | Runtime and generated package metadata are Git-ignored. CI uses synthetic fixtures. |
| Malicious configuration | Strict models, safe YAML loading, blocked tags/anchors/aliases, size limits, unknown-key rejection, and sensitive-key rejection. |
| Malicious bundle archive | Exact member allowlist, path and link checks, compressed and expanded size limits, compression-ratio limits, safe parsing, and SHA-256 verification. |
| Dependency compromise or known vulnerability | Pinned GitHub Actions, CodeQL, dependency review, `pip-audit`, generated CycloneDX SBOM artifacts, Dependabot alerts, and security-update pull requests. |
| Secret committed to Git | GitHub secret scanning and push protection, plus central runtime redaction and ignored runtime paths. |
| Protected branch bypass or history rewrite | Administrator-enforced pull requests, strict required checks, linear history, squash-only merges, and blocked force pushes and deletion. |

## Redaction policy

The redactor removes configured sensitive keys and common email, phone, token, device identifier, UUID, and secret assignment patterns. Values under sensitive setting labels are replaced entirely. Device serials are never persisted in clear text.

Pattern redaction is not a complete data-loss-prevention system. Users must review artifacts before sharing them. Screenshots are not part of the supported audit flow.

SHA-256 values, validated semantic setting identifiers, and tool-generated 32-character job, operation, and transaction identifiers remain visible only under their exact typed keys. Integrity and report correlation depend on those values. The same strings under any other key are redacted as untrusted identifiers.

## Prohibited behavior

- Stored Garmin credential entry.
- Automated sign-in or account creation.
- Undocumented Garmin cloud endpoints.
- Remote Appium endpoints.
- ADB push or shell mutation.
- Generic Appium execute, text entry, or coordinate tapping.
- Unattended research sessions.
- Physical watch or account writes.
- Personal health, contact, network, payment, or location fixtures.
- YAML object tags, anchors, aliases, symbolic links, executable archive payloads, and archive paths outside the bundle root.

## Future write gate

A proposed physical write adapter must remain blocked until written Garmin authorization or qualified legal review exists, a recoverable pre-change backup is demonstrated, every attempt is durably journaled, verification independently re-reads state, rollback survives injected failures, idempotency is proven, and a physical Enduro 2 test matrix passes. The change requires an explicit Class 4 ADR and human approval.
