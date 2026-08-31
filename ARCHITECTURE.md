# Architecture

## Current scope

The current system combines a local, opt-in, read-only Phase 0 research probe with a transport-free configuration and planning engine. It records sanitized evidence, creates integrity-checked capture bundles, compares desired states, and generates plans with no automatic operations. It cannot write to the phone, watch, or Garmin account.

## Trust boundaries

1. The user controls Android authentication and pairing in Garmin Connect.
2. ADB supplies device and installed-package metadata.
3. A loopback-only Appium server exposes UiAutomator2 accessibility data and visible navigation controls.
4. The read-only audit service validates the exact package, authentication state, watch identity, and expected screens.
5. The redaction service sanitizes all data before persistence.
6. Runtime artifacts remain local and Git-ignored.
7. The simulation engine has no dependency on ADB, Appium, or the read-only audit service.
8. Configuration, bundle, archive, comparison, and planning services run before any ADB or Appium service is constructed.
9. Imported archives are untrusted until their structure, paths, payload limits, configuration, and checksums pass validation.

## Components

| Component | Responsibility |
| --- | --- |
| `AdbService` | Read ADB device state, properties, installed packages, and app metadata. |
| `AppiumService` | Create state-preserving loopback sessions and expose read-only navigation primitives. |
| `GarminAppDiscoveryService` | Accept only the exact Garmin Connect Android package. |
| `UiDiscoveryService` | Detect authentication, parse structured setting rows, classify risk, and sanitize diagnostics. |
| `GarminConnectNavigator` | Navigate exact visible controls and read watch identity. |
| `ReadOnlyAuditService` | Orchestrate the vertical slice and always close the session. |
| `CapabilityService` | Record only observed capabilities and explicitly block automatic writes. |
| `RedactionService` | Sanitize strings and recursive data structures before persistence or logging. |
| Persistence services | Write unique, atomic JSON, XML, Markdown, log, and journal artifacts. |
| `WriteSimulationService` | Exercise guarded transaction behavior against in-memory hooks only. |
| `ConfigurationService` | Safely load strict YAML or JSON, reject sensitive data, save sanitized YAML, and resolve ordered overlays. |
| `ConfigurationBundleService` | Capture, validate, import, and export sanitized bundles with coverage and checksum records. |
| `PlanningService` | Convert snapshots to observed state, compare bundles, enforce compatibility, and create read-only plans. |

## Read-only audit flow

1. Validate the selected ADB serial and authorized state.
2. Require the exact `com.garmin.android.apps.connectmobile` package.
3. Require a ready Appium endpoint on loopback.
4. Activate Garmin Connect without resetting data.
5. Stop if sign-in is required or authentication is uncertain.
6. Navigate through exact semantic controls to Garmin Devices.
7. Select the configured watch name and record visible firmware information.
8. Open the visible device settings root and parse structured label/value rows.
9. Build a capability manifest that marks write support unavailable.
10. Close the Appium session in all success and failure cases.
11. Redact and atomically save the snapshot, manifest, and reports.

## Offline configuration flow

1. Load a sanitized snapshot or strict desired-state configuration without constructing a device transport.
2. Reject oversized, linked, malformed, unknown, or sensitive configuration input.
3. Create a bundle with normalized YAML, explicit coverage, a human-readable summary, and SHA-256 records.
4. Validate every bundle before comparison, planning, export, or import.
5. Resolve overlays in supplied order and report every conflict.
6. Block incompatible models and unknown or unsupported settings.
7. Classify mismatches as guided, unsupported, unknown, or blocked. Automatic operations remain zero.
8. Redact and atomically save JSON and Markdown plan reports under the runtime directory.

## Write boundary

There is no production adapter interface implementation capable of mutation. `AdbService` has no push or shell-write method. `AppiumService` exposes no text-entry, coordinate-tap, or generic execute method. The simulation engine receives caller-provided in-memory hooks and is structurally separate from device services.

Any future physical write adapter is a Class 4 change. It requires authorization review, capability evidence, automatic pre-change backup, a durable journal, independent verification, failure injection, physical Enduro 2 testing, rollback evidence, and a new ADR.

## Target architecture

The product requirements describe broader backup, apply, verification, catalog, UI, and adapter layers. Only the offline read-only configuration foundation is implemented. Planned work is tracked in `FUTURE-UPGRADES.md`. Current code and reports must not imply a physical backup, automatic apply, rollback, or full watch inventory exists.
