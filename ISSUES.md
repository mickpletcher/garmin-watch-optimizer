# Issues

## Open

### ISSUE-001: Physical Enduro 2 acceptance is pending

The fake-device contract proves orchestration only. A disposable or sanitized physical test must confirm current Garmin Connect selectors, authentication markers, watch identity, firmware parsing, and settings row structure on Windows and macOS.

### ISSUE-002: Garmin Android automation authorization is not confirmed

No official source reviewed on 2026-08-30 affirmatively authorizes this exact local accessibility automation scenario. Android UI research remains opt-in, local, read-only, and disabled by default. Production use requires written authorization or qualified legal review.

### ISSUE-003: Localization is not supported

Authentication markers, navigation labels, device-family matching, and firmware labels currently use English text. Non-English UI must fail closed until locale-specific fixtures and selectors exist.

### ISSUE-004: Visible settings coverage is one screen

The audit records only the current device settings root reached by the navigator. It does not recurse through every settings category and must not claim complete watch coverage.
