# Garmin Watch Optimizer — Product Requirements Document

**Document status:** Initial build specification  
**Primary repository:** `mickpletcher/garmin-watch-optimizer`  
**Initial target device:** Garmin Enduro 2  
**Target desktop platforms:** Windows and macOS  
**License:** MIT

## 1. Purpose

Garmin Watch Optimizer is a cross-platform desktop application that treats a compatible Garmin watch configuration as code.

The product shall inspect the settings that a connected watch and the installed Garmin desktop/mobile ecosystem make available, represent the desired configuration in a human-readable file, compare the desired configuration with the watch, safely apply supported changes, and verify the final state.

The central use case is repeatable recovery: after a factory reset, watch replacement, or accidental setting change, the user should be able to select a saved configuration, preview the proposed changes, and restore as much of the preferred setup as the connected device supports.

The product should also make normal watch customization substantially easier than navigating long menus on the watch. The first release will focus on the Garmin Enduro 2 and especially on activity favorites, activity ordering, activity profiles, data screens, watch faces, controls, glances, hot keys, and common system settings.

## 2. Important Product Constraint

Garmin does not expose one documented public desktop API that can read and write every watch setting. Garmin Express is the Garmin desktop application for Windows and macOS, but many wearable settings are managed on the watch, in the Garmin Connect mobile app, or in the Connect IQ Store app. Garmin's own backup feature also varies by device and firmware.

Therefore, the implementation must not assume that every setting can be manipulated directly through Garmin Express. It shall use an adapter-based capability model and choose the safest available mechanism for each setting:

1. A documented Garmin interface or file format, when available.
2. Supported device storage access over USB/MTP, when safe and reversible.
3. Desktop UI automation of Garmin Express, when the required control is actually exposed there.
4. A guided, human-confirmed workflow for settings only available on the watch or in a mobile app.
5. Read-only reporting when no safe apply mechanism exists.

Reverse-engineered or undocumented write operations must be isolated behind an experimental adapter, disabled by default, clearly labeled, and never required for the minimum viable product (MVP).

## 3. Product Principles

- **Backup before mutation:** No change is applied until a recoverable pre-change snapshot is created or the user explicitly acknowledges why one cannot be created.
- **Plan before apply:** Every apply operation produces a readable change plan first.
- **Capability driven:** The UI and CLI show only operations supported for the detected model, firmware, platform, and connection method.
- **Configuration as code:** Desired state is portable, diffable, versionable, and understandable without the application.
- **Idempotent operation:** Applying the same configuration twice produces no additional changes on the second run.
- **No silent partial success:** Every requested setting receives a result: applied, already compliant, skipped, unsupported, requires user action, or failed.
- **Preserve unknown settings:** The tool changes only settings explicitly present in the chosen configuration unless the user requests strict synchronization.
- **Local-first privacy:** Configuration files and backups remain local by default. Cloud upload is opt-in.
- **Safe recovery:** Interrupted operations are resumable, and failed operations provide rollback or precise recovery instructions.
- **Extensible support:** Adding another Garmin model or firmware family should normally require a capability profile or adapter, not a rewrite of the application.

## 4. Goals

### 4.1 Primary goals

1. Detect a supported Garmin watch connected to a Windows PC or Mac.
2. Inventory the watch, Garmin software, connection method, firmware, and available configuration capabilities.
3. Export the current supported configuration into a portable configuration bundle.
4. Compare a saved desired configuration with the currently connected watch.
5. Generate a dry-run plan before changing anything.
6. Apply supported settings safely and verify the result.
7. Restore a preferred setup after a reset or replacement with minimal manual work.
8. Make high-value settings—especially activity favorites and ordering—easy to manage from a desktop UI.
9. Clearly guide the user through settings that cannot be automated safely.
10. Maintain an auditable log without exposing credentials or sensitive health data.

### 4.2 Secondary goals

- Support reusable profiles such as `Daily`, `Race`, `Trail Run`, `Expedition`, and `Battery Saver`.
- Allow selected setting groups to be applied without applying the entire configuration.
- Allow configuration comparison between two backups or two watches.
- Provide a plugin architecture for additional Garmin watches.
- Offer both a graphical interface and a scriptable command-line interface.

## 5. Non-Goals for the Initial Release

- Replacing Garmin Connect, Garmin Express, or the Connect IQ Store.
- Bypassing Garmin authentication, device security, paid content, licensing, or digital signatures.
- Editing completed activity history, wellness records, medical information, or Garmin cloud account data.
- Automating firmware installation without Garmin's supported workflow.
- Promising byte-for-byte migration between incompatible watch models.
- Installing pirated watch faces, maps, music, or Connect IQ applications.
- Requiring an unofficial Garmin cloud API for core operation.
- Performing destructive reset operations.
- Guaranteeing automation of controls that Garmin exposes only on a phone or directly on the watch.

## 6. Target Users and Core Scenarios

### 6.1 Primary user

A technically comfortable Garmin owner with a feature-rich watch who wants a repeatable, reviewable setup rather than manually reconstructing dozens of settings after a reset.

### 6.2 Core scenarios

#### Scenario A — Capture a known-good configuration

1. The user connects an Enduro 2 by USB and opens Garmin Watch Optimizer.
2. The application detects the watch, installed Garmin applications, and available capabilities.
3. The user selects **Create Backup**.
4. The application exports supported settings, records unsupported/unreadable areas, creates checksums, and saves a named bundle.
5. The user can inspect the generated YAML configuration and Markdown summary.

#### Scenario B — Restore after a factory reset

1. The user reconnects the reset watch and selects a previous bundle.
2. The application validates model, firmware, compatibility, and bundle integrity.
3. It displays a dry-run plan grouped by automated and manual actions.
4. The user approves the plan.
5. The application creates a pre-restore snapshot, applies safe automated changes, guides remaining steps, syncs as required, and verifies the outcome.

#### Scenario C — Optimize the activity list

1. The application displays all detected activities and apps.
2. The user marks their actual activities as favorites and reorders them using drag-and-drop.
3. The desired state might place `Trail Run`, `Run`, `Hike`, `Strength`, `Pool Swim`, and `Bike` at the top while retaining other activities below.
4. The application previews and applies the new favorites and order through the supported adapter.

#### Scenario D — Configure activity profiles

The user selects an activity and manages data screens, layouts, fields, alerts, auto features, satellite mode, routing, power mode, and other capabilities that the device exposes for that activity.

#### Scenario E — Manage watch faces

The user inventories installed watch faces, selects the active face when supported, configures supported Connect IQ properties, and receives guided steps for settings that can only be edited on-watch or in the Connect IQ mobile app.

#### Scenario F — Audit without changing

The user runs a read-only audit to compare the watch with a configuration and exports a report. No mutation is performed.

## 7. Functional Requirements

Requirement keywords **MUST**, **SHOULD**, and **MAY** indicate mandatory, recommended, and optional behavior respectively.

### FR-001 — Device and environment discovery

The application MUST:

- Detect supported Garmin devices connected by USB, including MTP and mass-storage modes where the operating system permits access.
- Identify device model, device identifier, firmware/software version, storage mode, and connection status when available.
- Detect Windows or macOS and the installed Garmin Express version and path.
- Detect whether Garmin Express is running and warn about access conflicts.
- Support multiple detected Garmin devices by requiring explicit device selection.
- Never guess which device should be modified.
- Provide actionable instructions when the cable is charge-only, the device is locked, MTP access is unavailable, or Garmin Express must be opened/closed.

### FR-002 — Capability discovery

The application MUST build a capability manifest for the selected device and session. Each setting or setting group MUST declare:

- Stable capability identifier.
- Display name and description.
- Read support: `full`, `partial`, `none`, or `unknown`.
- Write support: `automatic`, `guided`, `read-only`, `experimental`, or `unsupported`.
- Adapter and transport used.
- Supported values and validation rules, when discoverable.
- Whether a restart, Garmin sync, phone action, or watch confirmation is required.
- Model and firmware constraints.
- Risk classification.

The application MUST refuse a write when the relevant capability is absent or incompatible.

### FR-003 — Configuration export

The user MUST be able to export the current supported state as a bundle containing:

- `config.yaml`: normalized, declarative desired state.
- `manifest.json`: schema version, application version, device metadata, firmware, creation time, adapter versions, completeness, and checksums.
- `summary.md`: human-readable coverage, values, omissions, warnings, and restoration notes.
- `raw/`: optional native files or opaque snapshots required for lossless recovery, when legally and technically safe.
- `logs/`: optional sanitized capture log.

The application MUST allow the user to choose which setting groups are included. It MUST label every group as captured, partially captured, unavailable, or excluded.

### FR-004 — Declarative configuration file

The normalized configuration MUST use YAML for readability. JSON MAY be accepted as an import format. The file MUST:

- Include `schema_version`.
- Identify a source model without binding the configuration to a secret account identifier.
- Separate portable desired settings from device-specific raw artifacts.
- Support comments in user-authored YAML.
- Use stable semantic identifiers instead of screen coordinates or localized labels.
- Permit omitted properties; omission means preserve the current value.
- Permit an explicit reset-to-default operation only where safely supported.
- Support variable substitution for non-secret profile values.
- Reject unknown or invalid values by default, with a clear validation error.
- Preserve unknown future keys during round-trip editing where practical.

Example:

```yaml
schema_version: "1.0"
profile:
  name: "Mick Enduro 2 Daily"
  description: "Daily training and mountain-running configuration"

target:
  manufacturer: "Garmin"
  models:
    - "Enduro 2"
  minimum_firmware: null

apply_policy:
  mode: "merge"
  backup_before_apply: true
  verify_after_apply: true
  unsupported: "report"
  require_confirmation_for_high_risk: true

activities:
  favorites:
    - trail_run
    - run
    - hike
    - strength
    - pool_swim
    - bike
  order:
    - trail_run
    - run
    - hike
    - strength
    - pool_swim
    - bike
  profiles:
    trail_run:
      satellites: auto_select
      auto_pause: false
      data_screens:
        - layout: "4_fields"
          fields:
            - elapsed_time
            - distance
            - heart_rate
            - current_pace

watch_face:
  desired_id: null
  properties: {}

system:
  units: statute
  time_format: "12_hour"
```

### FR-005 — Backup catalog

The application MUST provide a local backup catalog with:

- User-defined name, description, and tags.
- Creation timestamp and source device metadata.
- Firmware and schema versions.
- Coverage and completeness score.
- Integrity status.
- Parent backup when created automatically before an apply.
- Search, sort, inspect, export, import, and delete operations.

Deletion MUST require confirmation and SHOULD use the operating system recycle bin/trash when possible.

### FR-006 — Configuration validation and migration

Before planning or applying, the application MUST:

- Validate syntax and schema.
- Validate values against the selected device capability manifest.
- Verify bundle checksums.
- Detect schema, application, model, and firmware incompatibilities.
- Offer a non-destructive schema migration when supported.
- Save migrated output as a new version unless the user explicitly replaces the original.
- Report properties that cannot be mapped to the target watch.

### FR-007 — Diff and dry-run plan

The application MUST compare current and desired state and classify each item as:

- `already_compliant`
- `will_change`
- `will_add`
- `will_remove`
- `requires_user_action`
- `unsupported`
- `unknown_current_value`
- `blocked`

The plan MUST show old and proposed values where both are readable, the adapter, risk, dependencies, expected sync/restart behavior, and whether rollback is supported. The user MUST be able to deselect individual changes or whole groups.

### FR-008 — Apply engine

The apply engine MUST:

- Require an explicit user approval after displaying the plan.
- Create and validate a pre-change backup.
- Acquire an exclusive per-device operation lock.
- Apply changes in dependency order.
- Persist a transaction journal after every step.
- Be resumable after application crash, device disconnect, or system restart.
- Use bounded retries only for operations known to be safe to repeat.
- Never retry ambiguous destructive writes automatically.
- Stop safely when model, firmware, connection, or observed UI differs from the approved plan.
- Offer rollback when a verified restoration method exists.
- Produce a complete per-setting result.

### FR-009 — Verification

After apply, the application MUST re-read every automatically verifiable setting. It MUST distinguish:

- Verified success.
- Applied but awaiting sync/restart/watch confirmation.
- Unable to verify.
- Verification mismatch.
- Rolled back.
- Failed and not rolled back.

A job MUST NOT be labeled successful if requested changes remain mismatched or unverified without a visible qualification.

### FR-010 — Activity and app list management

For devices that expose the necessary capabilities, the application MUST:

- Inventory activities and apps.
- Display favorites separately from the full list.
- Add or remove an activity from favorites.
- Reorder favorite activities.
- Reorder the broader activity/app list when supported.
- Preserve activities not mentioned in merge mode.
- Offer strict mode only with a preview of removals/reordering.
- Detect stable activity identifiers despite localized display names.
- Support custom and multisport activities without overwriting them accidentally.

The Enduro 2 activity favorites and ordering workflow is an MVP acceptance requirement, but guided execution is acceptable during the research release if safe automatic control cannot be demonstrated.

### FR-011 — Per-activity profile management

The application SHOULD manage the following when supported by the selected activity and watch:

- Data-screen count and order.
- Screen layout and data-field assignment.
- Map, elevation, music, virtual partner, and other special screens.
- Alerts and thresholds.
- Auto Lap, Auto Pause, Auto Climb, Auto Scroll, and similar automation.
- Satellite mode.
- Power mode.
- Routing and map behavior.
- Recording interval and activity-specific sensor behavior.
- Touch, button, lap-key, and timeout behavior.
- Sport-specific options.

The UI MUST derive controls from capability metadata because not all settings exist for all activities.

### FR-012 — Watch face management

The application SHOULD:

- Inventory built-in and installed Connect IQ watch faces where discoverable.
- Identify the active watch face where readable.
- Select an installed watch face where safely writable.
- Read and write documented Connect IQ app properties when exposed through an available supported surface.
- Export watch-face identity and configurable properties.
- Detect when a face is unavailable on the target model.
- Guide the user to Garmin Connect IQ or on-watch editing when automation is unavailable.

The tool MUST NOT copy or redistribute proprietary watch-face binaries. A backup may record store identifiers, versions, and property values so the user can reinstall through Garmin's supported channel.

### FR-013 — Additional setting domains

The architecture MUST support the following domains, although automatic write support may be phased:

| Domain | Examples | Initial expectation |
| --- | --- | --- |
| Controls | Add, remove, reorder control-menu items | Audit/guided, automate when proven safe |
| Glances/widgets | Visibility and order | Audit/guided, automate when proven safe |
| Hot keys | Button combinations and assigned actions | High-priority Enduro 2 support |
| System | Units, time, language, sounds, vibration, backlight, touch, USB mode | Capability driven |
| Display | Brightness, gesture, timeout, always-on behavior where applicable | Capability driven |
| Health/wellness | Activity tracking toggles, move alert, sleep settings, heart-rate behavior | Exclude sensitive history; settings only |
| User profile | Non-sensitive physiological preferences needed by the watch | Opt-in export with privacy warning |
| Sensors/accessories | Inventory, enabled state, preferred sensors | Never export pairing secrets |
| Connectivity | Wi-Fi/Bluetooth status and safe preferences | Never export passwords or authentication tokens |
| Safety/tracking | Feature status and emergency-contact references | Read-only by default; no contact data in portable config |
| Maps/navigation | Installed-map inventory and routing preferences | Do not copy licensed map content |
| Music | Provider/app inventory and playback preferences | Do not copy DRM media or credentials |
| Power Manager | Battery modes and per-activity power behavior | High-value Enduro 2 support |
| Connect IQ | Installed app/data-field/watch-face identifiers and settings | Reinstall only through supported Garmin channel |
| Workouts/courses | Inventory and references | Not a substitute for Garmin Connect content management |

### FR-014 — Guided actions

When a setting cannot be automated, the application MUST be able to create a guided action containing:

- Exact device/model-specific navigation instructions.
- Current value if known.
- Desired value.
- A checkbox or confirmation step.
- Optional screenshot/reference image owned or permitted for use.
- A verification step when the value can subsequently be read.

Guided actions MUST be part of the same transaction report and MUST NOT be represented as automatic success.

### FR-015 — Graphical user interface

The desktop GUI MUST provide:

- First-run compatibility and safety explanation.
- Device selector and connection status.
- Dashboard showing model, firmware, battery when available, Garmin software status, and capability coverage.
- Configuration explorer with search and setting-group navigation.
- Activity favorites editor with drag-and-drop ordering.
- Backup catalog.
- Side-by-side diff and dry-run plan.
- Apply progress, user-action prompts, verification results, and recovery guidance.
- Accessible keyboard navigation and screen-reader labels.
- Light and dark themes using native platform conventions where practical.

### FR-016 — Command-line interface

The application MUST provide a CLI suitable for scripting. Initial command surface:

```text
gwo devices list
gwo capabilities show --device <id>
gwo capture --device <id> --output <bundle>
gwo validate <config-or-bundle>
gwo diff <config-or-bundle> --device <id>
gwo plan <config-or-bundle> --device <id> --output <plan>
gwo apply <config-or-bundle> --device <id>
gwo verify <job-id>
gwo rollback <job-id>
gwo backups list
gwo report <job-id> --format markdown
```

The CLI MUST use meaningful exit codes, support JSON output, and avoid interactive prompts when `--non-interactive` is supplied. Mutation in non-interactive mode MUST still require an explicit approval flag and a valid pre-change backup policy.

### FR-017 — Reports and audit log

Every capture, plan, apply, verify, and rollback operation MUST receive a job identifier. The application MUST generate a sanitized Markdown and JSON report containing:

- Application, adapter, operating-system, device-model, and firmware versions.
- Start/end time and final status.
- Planned and actual results by setting.
- Warnings, user actions, failures, and recovery instructions.
- Backup identifiers and checksums.

Logs MUST redact tokens, credentials, Wi-Fi passwords, personal contact details, and sensitive health data.

### FR-018 — Import, export, and portability

- A configuration bundle MUST be exportable as a directory or ZIP archive.
- Import MUST defend against path traversal, decompression bombs, invalid links, executable payloads, and checksum mismatch.
- Raw device artifacts MUST be marked model/firmware specific.
- The application SHOULD offer a portability report before applying a configuration to another compatible model.
- User-defined configurations SHOULD be suitable for storage in Git, while raw backups and logs SHOULD be excluded by default through generated `.gitignore` guidance.

### FR-019 — Profiles and overlays

The product SHOULD support a base configuration plus named overlays. For example, a `Daily` base could be combined with a `Race` overlay that changes data screens, alerts, and satellite settings without duplicating every other preference.

Overlay order MUST be deterministic, conflicts MUST be reported, and the resolved configuration MUST be visible before apply.

### FR-020 — Updates and compatibility data

- The application MUST version its configuration schema and adapter interfaces.
- Compatibility profiles MUST be signed or shipped with application releases if remote updates are later supported.
- A compatibility update MUST NOT silently enable experimental writes.
- Unknown firmware MUST default to audit/read-only behavior until validated or explicitly enabled by the user for an experimental adapter.

## 8. Adapter Architecture Requirements

The core application MUST be independent from any one transport or automation method.

### 8.1 Required adapter interfaces

```text
DeviceDiscoveryAdapter
  discover() -> devices
  inspect(device) -> device_metadata

CapabilityAdapter
  probe(device, environment) -> capability_manifest

ConfigurationAdapter
  read(device, selectors) -> observed_state
  plan(observed_state, desired_state) -> operations
  apply(operation, journal) -> operation_result
  verify(operation) -> verification_result
  rollback(operation, backup) -> rollback_result
```

### 8.2 Planned adapter families

1. **Garmin Express adapter** — launches/detects Garmin Express and automates only confirmed desktop controls using Windows UI Automation or macOS Accessibility APIs.
2. **Garmin device-storage adapter** — reads/writes explicitly supported files over USB/MTP, with checksums and atomic replacement where possible.
3. **Native Garmin backup adapter** — detects and coordinates the watch/Garmin Connect backup-and-restore feature where the model supports it; this complements rather than replaces the normalized configuration.
4. **Connect IQ metadata adapter** — manages identifiers and documented settings without redistributing binaries.
5. **Guided on-watch adapter** — produces model-specific instructions and captures user confirmation.
6. **Simulator/fake adapter** — deterministic development and test device with no physical watch required.

### 8.3 UI automation rules

UI automation MUST:

- Use accessibility/control identifiers, roles, and text rather than fixed coordinates wherever possible.
- Validate the application name, version, window, page, and expected controls before each mutation.
- Stop on unexpected dialogs or layout changes.
- Capture diagnostic evidence with sensitive content redacted.
- Keep Windows and macOS selectors in separate versioned page-object modules.
- Support localization only after selectors and expected text are defined for that locale.
- Never enter stored Garmin credentials. Authentication remains user controlled.

Image matching and coordinate clicking MAY be used only as a clearly marked experimental fallback with explicit confirmation.

## 9. Backup and Recovery Model

Garmin's native backup can include sport profiles, widgets, user settings, workouts, and other supported data on compatible devices. Garmin Watch Optimizer MUST not claim that its normalized YAML is a byte-for-byte replacement for Garmin's native backup.

The product SHALL use two complementary layers:

1. **Native recovery layer:** Trigger, preserve, or guide Garmin's supported backup/restore workflow when available.
2. **Declarative recovery layer:** Capture readable preferences in a portable schema, apply supported settings, and guide the rest.

Before any mutation, the application MUST record whether each requested domain has:

- Native backup coverage.
- Declarative capture coverage.
- Verified rollback support.
- No known recovery mechanism.

High-risk changes with no recovery mechanism MUST require separate confirmation and MUST be disabled by default.

## 10. Data Model

The implementation SHOULD define typed domain models for:

- `DeviceIdentity`
- `Environment`
- `Capability`
- `ObservedConfiguration`
- `DesiredConfiguration`
- `ConfigurationOverlay`
- `BackupManifest`
- `ChangePlan`
- `Operation`
- `TransactionJournal`
- `VerificationResult`
- `CompatibilityIssue`
- `GuidedAction`

All persisted timestamps MUST use ISO 8601 UTC. Enumerations and stable identifiers MUST be separated from localized display strings.

## 11. Security and Privacy Requirements

- The application MUST operate locally by default and MUST NOT require telemetry.
- Telemetry, crash uploads, and update checks MUST be separately disclosed and configurable.
- Secrets MUST never be written to configuration files, bundles, logs, screenshots, or command history.
- Garmin account authentication MUST occur only in Garmin-owned interfaces unless Garmin later provides an approved authorization mechanism.
- Backup ZIP imports MUST be treated as untrusted input.
- Native files MUST be copied before parsing and never edited in place without a validated atomic procedure.
- Configuration and manifest parsing MUST use safe loaders; arbitrary object construction or code execution is prohibited.
- Plugins/adapters MUST have an explicit trust model before third-party loading is enabled.
- The application SHOULD support optional local encryption for backup bundles.
- Signing and checksum verification SHOULD be supported for configurations used in automated workflows.
- The release process MUST generate a software bill of materials and scan dependencies.

## 12. Reliability and Performance Requirements

- The application MUST remain responsive during device discovery, capture, apply, and verification.
- A disconnect MUST not corrupt the source configuration or leave an unjournaled operation.
- File writes MUST use temporary files, flush, checksum verification, and atomic rename where the device/filesystem supports them.
- Operations MUST be deterministic for the same device state, desired configuration, and adapter versions.
- A typical audit or plan SHOULD complete within 60 seconds after the device is ready, excluding Garmin sync time and user actions.
- Progress MUST be visible for operations longer than two seconds.
- Error messages MUST state what failed, whether anything changed, and what the user should do next.

## 13. Accessibility and Internationalization

- All interactive controls MUST be keyboard reachable.
- Color MUST not be the only indicator of plan or result status.
- Text and controls SHOULD meet WCAG 2.2 AA contrast and labeling expectations.
- User-facing strings MUST be externalized for localization.
- Parsing and capability identifiers MUST not depend on localized activity names.
- Dates, times, and units may be displayed in the user's locale while persisted values remain canonical.

## 14. Recommended Technical Direction

Codex should validate this direction during the technical spike before locking dependencies:

- **Language:** Python 3.12 or newer.
- **Desktop UI:** PySide6.
- **CLI:** Typer or an equivalent typed CLI framework.
- **Models/schema:** Pydantic with generated JSON Schema.
- **YAML:** `ruamel.yaml` if comment-preserving round trips are required; otherwise a safe YAML parser.
- **Storage:** SQLite for catalog/job metadata; user-visible configuration remains file based.
- **Windows automation:** Microsoft UI Automation through a maintained Python bridge.
- **macOS automation:** Accessibility APIs through PyObjC.
- **Packaging:** Signed MSIX/installer for Windows and signed/notarized app bundle or DMG for macOS.
- **Testing:** pytest, property-based configuration tests, golden-file schema tests, and fake-device contract tests.

Platform automation code MUST not leak into the domain or planning layers. The CLI and GUI MUST call the same application service layer.

## 15. Testing Requirements

### 15.1 Automated tests

- Unit tests for schema validation, normalization, overlays, diffing, dependency ordering, and redaction.
- Contract tests that every adapter passes using shared fixtures.
- Golden tests for configuration and report formats.
- Property-based tests for idempotency and round-trip serialization.
- Failure-injection tests for disconnect, timeout, partial write, stale UI, bad checksum, unknown firmware, and interrupted resume.
- Security tests for malicious YAML/ZIP input and sensitive-data leakage.
- Cross-platform CI for supported Python versions and operating systems.

### 15.2 Hardware-in-the-loop tests

The Enduro 2 validation matrix MUST include:

- Freshly paired watch.
- Populated, known-good watch.
- Watch after factory reset.
- Current supported firmware and at least one earlier available fixture/recording.
- Windows and macOS.
- Garmin Express open and closed.
- MTP/USB reconnect during read and during a safe test write.
- Applying the same configuration twice.
- Rollback from an intentionally failed multi-step plan.

Tests MUST use non-sensitive test accounts and sanitized fixtures.

## 16. MVP Scope

The MVP is complete when all of the following are delivered:

1. Windows and macOS application shells share one domain engine.
2. Enduro 2 detection and environment diagnostics work reliably.
3. Capability probing produces a saved manifest.
4. Current supported state can be captured into a valid bundle.
5. YAML validation, diff, dry-run plan, job journal, and Markdown/JSON reports work.
6. Activity inventory, favorite selection, and ordering have a complete desktop workflow.
7. At least one high-value setting group can be automatically applied and verified on a physical Enduro 2 using a safe adapter.
8. Non-automatable activity changes are represented as model-specific guided actions.
9. Automatic pre-change backup and post-change verification are enforced.
10. Applying the same configuration a second time results in zero planned automatic changes.
11. Fake-device tests cover successful apply, partial failure, rollback, disconnect, and resume.
12. Installable development builds are produced for Windows and macOS.

Watch-face configuration, all activity-profile settings, and broad model support are not required to declare the MVP complete unless the technical spike confirms safe access and the project explicitly promotes them into scope.

## 17. Acceptance Criteria

### AC-001 — Safe read-only audit

Given an Enduro 2 is connected, when the user runs an audit, then the tool identifies the device and firmware, reports capability coverage, saves no changes to the watch, and produces a sanitized report.

### AC-002 — Configuration capture

Given a configured Enduro 2, when the user captures a bundle, then the bundle passes schema and checksum validation and explicitly lists both captured and uncaptured setting groups.

### AC-003 — Favorites plan

Given a desired favorites list different from the observed list, when the user requests a plan, then the plan shows each addition, removal, and order change without modifying the watch.

### AC-004 — Apply protection

Given a plan containing changes, when the user applies it, then a valid pre-change snapshot exists before the first mutation, and the job journal records every attempted operation.

### AC-005 — Verification

Given an automatically applied setting, when apply completes, then the value is re-read and classified as verified or mismatched; it is never marked verified based only on a click or write attempt.

### AC-006 — Idempotency

Given a successful apply, when the same configuration is planned again against the unchanged watch, then no automatic changes are proposed.

### AC-007 — Unsupported settings

Given a configuration property unsupported by the watch or adapter, when planning occurs, then the item is reported as unsupported or guided, no unsafe write is attempted, and other independent supported changes may proceed only with the user's approval.

### AC-008 — Interrupted apply

Given the watch disconnects during a multi-step operation, when the application detects the disconnect, then it stops safely, persists state, reports whether a write may have occurred, and offers verified resume or rollback paths.

### AC-009 — Cross-model protection

Given a bundle from an incompatible model, when the user selects it, then the application blocks direct apply and provides a portability report rather than guessing mappings.

### AC-010 — Secret redaction

Given configurations, logs, screenshots, and reports are exported, then automated tests confirm that configured secret patterns and sensitive fields are absent.

## 18. Delivery Phases

### Phase 0 — Feasibility and read-only research

- Document exactly what Garmin Express exposes on current Windows and macOS versions.
- Map Enduro 2 USB/MTP files and native backup behavior using disposable test data.
- Identify settings available through Garmin Connect and Connect IQ but not Garmin Express.
- Build device discovery and a read-only capability probe.
- Record evidence for every proposed write path.
- Decide which single setting group is safe for the first automatic apply.

**Exit gate:** No production write adapter is enabled until capture, rollback, and verification have been demonstrated on a physical Enduro 2.

### Phase 1 — Configuration engine

- Typed schema and example configurations.
- Bundle capture/import/export.
- Diff, validation, plan, overlays, journals, and reports.
- Fake-device adapter and exhaustive failure tests.

### Phase 2 — Enduro 2 activity experience

- Activity inventory and favorites editor.
- Ordering and selected per-activity settings.
- First verified write adapter.
- Guided fallback for remaining settings.

### Phase 3 — Broader customization

- Data screens and fields.
- Controls, glances, hot keys, power modes, and system preferences.
- Watch-face/Connect IQ inventory and supported properties.
- Native Garmin backup coordination.

### Phase 4 — Compatibility expansion

- Additional Garmin watch models.
- Portability rules between compatible families.
- Signed compatibility-data updates.
- Optional encrypted backup and profile sharing.

## 19. Required Research Artifacts

Before implementing device writes, Codex MUST add:

- `docs/COMPATIBILITY.md` — device/firmware/platform capability matrix.
- `docs/ADAPTERS.md` — adapter contracts, trust boundaries, and transports.
- `docs/ENDURO2-RESEARCH.md` — observed Enduro 2 behavior and evidence.
- `docs/SECURITY.md` — threat model, secret handling, and import defenses.
- `schemas/config.schema.json` — generated configuration schema.
- `examples/enduro2.example.yaml` — documented, non-personal sample.
- Architecture decision records for any undocumented or experimental access method.

Each capability row MUST cite the Garmin documentation or sanitized empirical test that supports it and include the last validated Garmin Express and firmware versions.

## 20. Codex Implementation Instructions

When using this document to build the product, Codex shall:

1. Inspect the repository and this requirements document before proposing architecture.
2. Start with Phase 0 and the fake/read-only paths; do not begin by scripting clicks or writing unknown device files.
3. Create a vertical slice through discovery, capture, diff, plan, approval, fake apply, verify, and report.
4. Keep commits and pull requests small, testable, and mapped to requirement identifiers.
5. Add or update tests with every behavioral change.
6. Update `README.md`, `CHANGELOG.md`, compatibility documentation, and example configurations when changes materially affect users.
7. Record assumptions and unresolved Garmin constraints explicitly rather than inventing APIs or declaring unsupported settings complete.
8. Treat physical-device mutation as a protected integration test requiring an explicit opt-in flag.
9. Never use real credentials, personal health data, emergency contacts, or Wi-Fi secrets in fixtures.
10. Stop and request human review before enabling any experimental write path by default.

## 21. Definition of Done for a Setting Capability

A setting is not considered supported until all of the following are true:

- A stable semantic identifier and typed value model exist.
- Model and firmware applicability are documented.
- Current value can be read, or inability to read is clearly represented.
- Desired value is validated before execution.
- Diff and plan output are understandable.
- The apply mechanism is documented and risk classified.
- Pre-change recovery coverage is known.
- Verification checks the resulting state independently of the write attempt.
- Idempotency is tested.
- Failure, disconnect, resume, and rollback behavior are tested as applicable.
- Windows and/or macOS support is accurately declared.
- The capability matrix and user documentation are updated.

## 22. Open Questions to Resolve During Phase 0

1. Which Enduro 2 settings, if any, can current Garmin Express versions directly modify on Windows and macOS?
2. Which settings are represented in accessible device files, and which file writes are officially supported?
3. Can activity favorites and ordering be read and safely changed through a supported desktop-accessible artifact, or must the initial workflow be guided?
4. What portions of Garmin's native Enduro 2 backup can be initiated, exported, enumerated, or verified from the desktop?
5. Which Connect IQ watch-face properties are accessible outside the mobile apps, and is a documented desktop path available?
6. How do firmware updates change identifiers, file formats, menu layouts, and native-backup coverage?
7. What settings require a watch restart, Garmin sync, phone sync, or direct confirmation on the watch?
8. Which configuration properties are portable to newer Garmin models, and how should mappings be reviewed?
9. What is the safest useful first automatic write for the physical-device MVP?

## 23. Reference Basis

This specification is grounded in the following Garmin documentation available at the time of writing:

- [Enduro 2: Back Up and Restore Settings](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-EE48B393-454D-4F32-B8B0-F598F2E8CB0A.html)
- [Enduro 2: Customizing Activities and Apps](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-25FA2988-33F2-4FC9-92FA-E457CBDB9E72.html)
- [Enduro 2: Adding or Removing a Favorite Activity](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-B1501DD1-3616-4171-8814-07340761F494.html)
- [Enduro 2: Changing the Order of an Activity](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-2B7CD712-3EAA-4A09-B289-CA9BB278DEBD.html)
- [Enduro 2: Customizing Data Screens](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-638CD68D-11B0-4D9C-B8B7-E28D15EC4566.html)
- [Garmin Connect IQ: Properties and App Settings](https://developer.garmin.com/connect-iq/core-topics/properties-and-app-settings/)
- [Garmin Developer Programs](https://developer.garmin.com/)

Documentation confirms that Enduro 2 supports favorites, activity ordering, per-activity customization, and native backup/restore. It does not establish a public desktop API for controlling all of those settings. Phase 0 must validate the actual desktop control surface before implementation claims automatic support.
