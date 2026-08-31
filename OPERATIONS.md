# Operations

## Operating mode

The supported operating mode is local read-only research. Physical writes are blocked. Android UI research is disabled by default.

## Startup

1. Install Python and project dependencies.
2. Install Android Platform Tools.
3. Start Appium locally with UiAutomator2.
4. Connect one authorized Android phone over USB.
5. Sign in and pair the Enduro 2 manually in Garmin Connect.
6. Run `garmin-opt doctor`.
7. Review the policy notice in `README.md` and `docs/SECURITY.md`.
8. Run the audit with the explicit research flag.

## Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `GARMIN_OPT_APPIUM_URL` | `http://127.0.0.1:4723` | Local Appium endpoint. Non-loopback hosts are rejected. |
| `GARMIN_OPT_RUNTIME_DIR` | `runtime` | Local artifact root. |
| `GARMIN_OPT_DIAGNOSTICS` | `0` | Save sanitized UI hierarchy diagnostics when set to `1`. |
| `GARMIN_OPT_ENABLE_ANDROID_UI_RESEARCH` | `0` | Explicitly enable the GUI audit and CLI audit without the one-run flag. |
| `GARMIN_OPT_TARGET_WATCH` | `Enduro 2` | Exact or unique partial watch name to select. |
| `GARMIN_OPT_HARDWARE_TESTS` | unset | Enable the read-only hardware smoke test when set to `1`. |

## Failure behavior

- Missing or unauthorized ADB device: stop without opening Garmin Connect.
- Multiple devices without `--serial`: stop and require an explicit target.
- Device serial discovery: redacted by default; `garmin-opt adb devices --show-serial` is an explicit sensitive-output opt-in.
- Wrong or missing Garmin package: stop. Connect IQ is not accepted as Garmin Connect.
- Non-loopback Appium endpoint: stop before network access.
- Appium not ready: stop before session creation.
- Sign-in required or uncertain: close the session and stop without further navigation.
- Unexpected control or screen: close the session and report the missing semantic control.
- Persistence failure: fail the operation. Do not report success.
- Simulation ambiguity: journal the ambiguity, restore the in-memory value, verify restoration, and fail loudly.

## Artifact handling

Artifacts are local and Git-ignored. They are not encrypted. The shared redaction layer reduces exposure but cannot guarantee removal of every personal value. Review files manually before sharing. Delete them using normal operating-system file controls when no longer needed.

## Recovery

The read-only audit does not change watch state. If a session fails, close Appium, reopen Garmin Connect manually, confirm the watch is connected, and rerun `garmin-opt doctor`. A failed simulation affects only process memory and its local journal.
