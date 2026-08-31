# Garmin Watch Optimizer

Garmin Watch Optimizer is an early read-only research tool for discovering visible Garmin Enduro 2 settings through a locally installed Garmin Connect Android app.

It does not change the watch. It does not automate sign-in. It does not call undocumented Garmin cloud APIs. The only write workflow is an in-memory simulation with no ADB or Appium transport.

## Current status

The project is in Phase 0. It currently provides:

- Exact Garmin Connect Android package validation.
- ADB device selection with explicit serial validation.
- Loopback-only Appium sessions that preserve app state.
- Sign-in detection that stops before navigation when authentication is missing or uncertain.
- Semantic navigation to Garmin Devices, the selected Enduro 2, and its visible settings page.
- Read-only watch model and firmware discovery.
- Sanitized snapshots, capability manifests, Markdown reports, JSON reports, diagnostics, logs, and simulation journals.
- A fake-device contract test covering the complete read-only flow.
- Windows and macOS CI with an enforced 85 percent domain-layer coverage floor.

The project does not yet provide configuration bundles, dry-run plans, physical backups, Garmin Express automation, USB/MTP adapters, or watch setting writes.

## Garmin authorization boundary

Garmin's published terms do not clearly authorize local accessibility automation of the Garmin Connect Android app. They also do not clearly prohibit this exact local read-only scenario. The project does not claim Garmin approval.

Android UI research is therefore:

- Disabled by default.
- Explicitly opt-in.
- Local and loopback-only.
- Read-only.
- Limited to a Garmin app session the user authenticated manually.
- Prohibited from using undocumented Garmin cloud endpoints or changing the watch or account.

Production Android automation or any physical write support requires written Garmin authorization or qualified legal review plus a separate security decision. See [ADR-002](docs/decisions/ADR-002-android-ui-research-boundary.md) and [Security](docs/SECURITY.md).

Official references last reviewed on 2026-08-30:

- [Garmin Terms of Use](https://www.garmin.com/en-US/legal/terms-of-use/)
- [Garmin Connect Privacy Policy](https://www.garmin.com/en-US/privacy/connect/policy/)
- [Garmin Developer Programs](https://developer.garmin.com/)

This project is not affiliated with or endorsed by Garmin. This is not legal advice.

## Requirements

- Python 3.12 or newer.
- Android SDK Platform Tools with `adb` on `PATH`.
- Node.js and npm for the local Appium server.
- Appium with the UiAutomator2 driver.
- Physical Android phone with Garmin Connect installed and manually signed in.
- Enduro 2 paired to Garmin Connect.

## Windows setup

```powershell
./scripts/setup_windows.ps1 -InstallDev
npm install -g appium
appium driver install uiautomator2
appium
```

## macOS setup

```bash
./scripts/setup_macos.sh --dev
npm install -g appium
appium driver install uiautomator2
appium
```

The Appium endpoint must resolve to `localhost`, `127.0.0.1`, or `::1`. Remote endpoints are blocked.

## Check the environment

```powershell
garmin-opt doctor
garmin-opt adb devices
garmin-opt garmin detect --serial <adb-serial>
garmin-opt appium check
```

Device serials are redacted by default and always redacted from persisted artifacts. If multiple Android devices are connected, explicitly display serials for target selection:

```powershell
garmin-opt adb devices --show-serial
```

Treat that terminal output as sensitive.

## Run the read-only audit

Review the authorization boundary above first. Then run:

```powershell
garmin-opt audit --serial <adb-serial> --watch "Enduro 2" --enable-android-ui-research
```

The equivalent persistent opt-in for the current shell is:

```powershell
$env:GARMIN_OPT_ENABLE_ANDROID_UI_RESEARCH = "1"
garmin-opt audit --serial <adb-serial> --watch "Enduro 2"
```

The audit stops if Garmin Connect shows a sign-in screen or authentication cannot be confirmed. Sign in manually in Garmin Connect. Never provide credentials to this tool.

## Launch the GUI

The GUI audit button remains disabled unless the environment opt-in is set before launch.

```powershell
$env:GARMIN_OPT_ENABLE_ANDROID_UI_RESEARCH = "1"
garmin-opt gui
```

## Run the write simulation

The simulation uses an in-memory dictionary. It cannot access ADB, Appium, Garmin Connect, or the watch.

```powershell
garmin-opt simulate-write-test --confirm-simulation
garmin-opt simulate-write-test --confirm-simulation --simulate-failure ambiguous
```

There is no `write-test` command and no physical write adapter.

## Runtime artifacts

All runtime artifacts stay under `runtime/` by default and are ignored by Git:

- `runtime/snapshots`
- `runtime/manifests`
- `runtime/reports`
- `runtime/diagnostics`
- `runtime/journals`
- `runtime/logs`

Every persistence service uses the same recursive redaction policy and atomic file replacement. Review artifacts before sharing them because no pattern-based redactor can guarantee removal of every personal value.

## Validation

```powershell
python -m pytest
python -m ruff check .
python -m mypy src
./scripts/docs-check.ps1
```

The default test run skips the hardware smoke test. Run the read-only hardware prerequisite test explicitly:

```powershell
$env:GARMIN_OPT_HARDWARE_TESTS = "1"
python -m pytest -m hardware --no-cov
```

No hardware test performs a watch write.

## Documentation

- [Requirements](REQUIREMENTS.md)
- [Architecture](ARCHITECTURE.md)
- [Validation](VALIDATION.md)
- [Operations](OPERATIONS.md)
- [Compatibility evidence](docs/COMPATIBILITY.md)
- [Adapter boundaries](docs/ADAPTERS.md)
- [Enduro 2 research](docs/ENDURO2-RESEARCH.md)
- [Security model](docs/SECURITY.md)
