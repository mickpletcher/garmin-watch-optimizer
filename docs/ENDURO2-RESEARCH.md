# Enduro 2 Research

## Confirmed from official documentation

Garmin documents Enduro 2 features for backup and restore, activity customization, favorite activities, activity ordering, and data screens:

- [Back Up and Restore Settings](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-EE48B393-454D-4F32-B8B0-F598F2E8CB0A.html)
- [Customizing Activities and Apps](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-25FA2988-33F2-4FC9-92FA-E457CBDB9E72.html)
- [Adding or Removing a Favorite Activity](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-B1501DD1-3616-4171-8814-07340761F494.html)
- [Changing the Order of an Activity](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-2B7CD712-3EAA-4A09-B289-CA9BB278DEBD.html)
- [Customizing Data Screens](https://www8.garmin.com/manuals/webhelp/GUID-2CD92989-7336-4BF3-96CC-50DDBD63B109/EN-US/GUID-638CD68D-11B0-4D9C-B8B7-E28D15EC4566.html)

These documents establish user-visible watch features. They do not establish a public desktop API or authorize this project to automate those features.

## Current synthetic evidence

The fake-device contract models this visible path:

1. Authenticated Garmin Connect home.
2. More.
3. Garmin Devices.
4. Enduro 2, connected.
5. Software Version.
6. Device Settings.
7. Structured settings rows for Units, Language, and Battery Saver.

The firmware value `18.16` in the fixture is synthetic test data. It is not a claim about a current physical watch.

## Physical research checklist

- Record host OS and version.
- Record Android version without retaining the device serial.
- Record Garmin Connect package and version.
- Record Enduro 2 firmware.
- Confirm manual sign-in is complete before starting.
- Confirm every navigation control by accessibility label or resource identifier.
- Capture sanitized hierarchy evidence only with diagnostics explicitly enabled.
- Confirm the audit causes no setting change, sync request, account update, or watch prompt.
- Repeat on Windows and macOS.
- Record selector drift and stop on any unexpected screen.

## Unresolved questions

- Which Enduro 2 settings are visible and readable in current Garmin Connect releases?
- Does visible firmware information have stable accessibility structure?
- Which settings require navigation beyond the current root?
- What does Garmin Express expose on current Windows and macOS versions?
- Which USB/MTP artifacts are documented and safe to copy for read-only research?
- What is covered by native backup for current Enduro 2 firmware?
