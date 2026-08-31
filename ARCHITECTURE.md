# Architecture

## Current scope

The current system is a local, opt-in, read-only Phase 0 research probe. It inspects the visible accessibility hierarchy of a manually authenticated Garmin Connect Android app. It records sanitized evidence. It cannot write to the phone, watch, or Garmin account.

## Trust boundaries

1. The user controls Android authentication and pairing in Garmin Connect.
2. ADB supplies device and installed-package metadata.
3. A loopback-only Appium server exposes UiAutomator2 accessibility data and visible navigation controls.
4. The read-only audit service validates the exact package, authentication state, watch identity, and expected screens.
5. The redaction service sanitizes all data before persistence.
6. Runtime artifacts remain local and Git-ignored.
7. The simulation engine has no dependency on ADB, Appium, or the read-only audit service.

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

## Write boundary

There is no production adapter interface implementation capable of mutation. `AdbService` has no push or shell-write method. `AppiumService` exposes no text-entry, coordinate-tap, or generic execute method. The simulation engine receives caller-provided in-memory hooks and is structurally separate from device services.

Any future physical write adapter is a Class 4 change. It requires authorization review, capability evidence, automatic pre-change backup, a durable journal, independent verification, failure injection, physical Enduro 2 testing, rollback evidence, and a new ADR.

## Target architecture

The product requirements describe future configuration, planning, backup, and adapter layers. Those layers are not implemented. Planned work is tracked in `FUTURE-UPGRADES.md`. Current code and reports must not imply they exist.
