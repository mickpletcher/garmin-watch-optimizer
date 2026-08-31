# Compatibility Evidence

This matrix records evidence. It does not infer support from passing unit tests.

| Component | Version or target | Windows | macOS | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| Python | 3.12+ | CI configured | CI configured | CI workflow | Automated pending first GitHub run |
| Android Platform Tools | Current user installation | Expected | Expected | ADB unit tests and doctor command | Physical pending |
| Appium | Local server with UiAutomator2 | Expected | Expected | Loopback policy and fake contract | Physical pending |
| Garmin Connect Android | Exact package `com.garmin.android.apps.connectmobile` | Expected | Expected | Exact package contract test | Version-specific physical pending |
| Garmin Enduro 2 | Model label `Enduro 2` | Target | Target | Synthetic UI fixture only | Physical pending |
| Enduro 2 firmware | Unknown | Unknown | Unknown | No sanitized physical evidence recorded | Pending |
| Garmin Express | Current release | Unknown | Unknown | Not researched in this implementation | Pending |
| USB/MTP artifacts | Enduro 2 | Unknown | Unknown | No file inventory recorded | Pending |
| Native Garmin backup | Enduro 2 | Unknown | Unknown | Official manual establishes device feature, not desktop automation coverage | Pending |

## Rules

- Synthetic fixtures prove parser and orchestration behavior only.
- A compatibility row changes to validated only after recording the Garmin app version, watch firmware, host OS, observed controls, sanitized evidence identifier, and validation date.
- Unknown Garmin Connect versions and firmware remain read only.
- No compatibility row can enable writes. That requires a separate Class 4 decision and physical safety evidence.
