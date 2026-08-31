from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from garmin_optimizer.config import AppConfig
from garmin_optimizer.exceptions import AndroidUiResearchDisabledError, BundleValidationError, OptimizerError
from garmin_optimizer.logging_utils import setup_logging
from garmin_optimizer.models import DiscoveredSetting, RiskLevel
from garmin_optimizer.services.adb_service import AdbService
from garmin_optimizer.services.appium_service import AppiumService
from garmin_optimizer.services.bundle_service import ConfigurationBundleService
from garmin_optimizer.services.capability_service import CapabilityService
from garmin_optimizer.services.configuration_service import ConfigurationService
from garmin_optimizer.services.garmin_app_discovery import GarminAppDiscoveryService
from garmin_optimizer.services.journal_service import TransactionJournalService
from garmin_optimizer.services.planning_service import PlanningService
from garmin_optimizer.services.read_only_audit import ReadOnlyAuditService
from garmin_optimizer.services.redaction import RedactionService
from garmin_optimizer.services.report_service import PocReportService
from garmin_optimizer.services.snapshot_service import SettingsSnapshotService
from garmin_optimizer.services.ui_discovery import UiDiscoveryService
from garmin_optimizer.services.write_simulation import SimulationHooks, WriteSimulationService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="garmin-opt")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")

    adb = sub.add_parser("adb")
    adb_sub = adb.add_subparsers(dest="adb_command", required=True)
    devices = adb_sub.add_parser("devices")
    devices.add_argument("--show-serial", action="store_true")

    garmin = sub.add_parser("garmin")
    garmin_sub = garmin.add_subparsers(dest="garmin_command", required=True)
    detect = garmin_sub.add_parser("detect")
    detect.add_argument("--serial", default=None)

    appium = sub.add_parser("appium")
    appium_sub = appium.add_subparsers(dest="appium_command", required=True)
    appium_sub.add_parser("check")

    audit = sub.add_parser("audit")
    audit.add_argument("--serial", default=None)
    audit.add_argument("--watch", default=None)
    audit.add_argument("--enable-android-ui-research", action="store_true")

    capture = sub.add_parser("capture")
    capture.add_argument("--snapshot", required=True)
    capture.add_argument("--name", required=True)
    capture.add_argument("--description", default="")
    capture.add_argument("--export-zip", action="store_true")

    validate = sub.add_parser("validate")
    validate.add_argument("path")

    compare = sub.add_parser("compare")
    compare.add_argument("older")
    compare.add_argument("newer")

    plan = sub.add_parser("plan")
    plan.add_argument("configuration")
    plan.add_argument("--snapshot", required=True)
    plan.add_argument("--overlay", action="append", default=[])

    bundle = sub.add_parser("bundle")
    bundle_sub = bundle.add_subparsers(dest="bundle_command", required=True)
    bundle_export = bundle_sub.add_parser("export")
    bundle_export.add_argument("path")
    bundle_import = bundle_sub.add_parser("import")
    bundle_import.add_argument("path")

    simulate = sub.add_parser("simulate-write-test")
    simulate.add_argument("--confirm-simulation", action="store_true")
    simulate.add_argument(
        "--simulate-failure",
        choices=["none", "ambiguous", "verification", "restore"],
        default="none",
    )

    sub.add_parser("gui")
    return parser


def _base_services() -> tuple[AppConfig, RedactionService]:
    config = AppConfig.from_env()
    redactor = RedactionService()
    setup_logging(config.logs_dir, redactor)
    return config, redactor


def _select_device(adb: AdbService, serial: str | None):
    return adb.select_device(adb.list_devices(), serial)


def _offline_services(
    config: AppConfig,
    redactor: RedactionService,
) -> tuple[ConfigurationService, ConfigurationBundleService, PlanningService]:
    configuration = ConfigurationService(redactor)
    bundles = ConfigurationBundleService(
        bundles_dir=config.bundles_dir,
        imports_dir=config.imports_dir,
        exports_dir=config.exports_dir,
        configuration=configuration,
        redactor=redactor,
    )
    planning = PlanningService(config.plans_dir, redactor)
    return configuration, bundles, planning


def _require_research_opt_in(args: argparse.Namespace, config: AppConfig) -> None:
    if not args.enable_android_ui_research and not config.android_ui_research_enabled:
        raise AndroidUiResearchDisabledError(
            "Android UI research is disabled. Review docs/SECURITY.md, then pass "
            "--enable-android-ui-research or set GARMIN_OPT_ENABLE_ANDROID_UI_RESEARCH=1."
        )


def _simulate_write(config: AppConfig, redactor: RedactionService, args: argparse.Namespace) -> int:
    setting = DiscoveredSetting(
        id="simulation.units",
        screen_path=["Simulation"],
        label="Units",
        current_value="Statute",
        selectable_values=["Statute", "Metric"],
        confidence=1.0,
        risk_level=RiskLevel.LOW,
        writable_candidate=True,
        notes="In-memory simulation fixture. No device transport exists.",
    )
    state_value = "Statute"
    call_count = 0

    def set_value(_: DiscoveredSetting, value: str) -> None:
        nonlocal call_count, state_value
        call_count += 1
        if args.simulate_failure == "ambiguous" and call_count == 1:
            state_value = value
            raise RuntimeError("injected transport failure after simulated mutation")
        if args.simulate_failure == "verification" and call_count == 1:
            return
        if args.simulate_failure == "restore" and call_count > 1:
            return
        state_value = value

    hooks = SimulationHooks(
        read_current=lambda _: state_value,
        list_values=lambda _: ["Statute", "Metric"],
        set_value=set_value,
    )
    journal = TransactionJournalService(config.journals_dir, redactor)
    transaction = WriteSimulationService().execute(
        setting=setting,
        temporary_value="Metric",
        user_confirmed=args.confirm_simulation,
        hooks=hooks,
        journal=journal,
    )
    print(transaction.model_dump_json(indent=2))
    print(f"Journal: {journal.path_for(transaction)}")
    print("Device transport used: No")
    return 0


def run(args: argparse.Namespace) -> int:
    config, redactor = _base_services()

    if args.command == "simulate-write-test":
        return _simulate_write(config, redactor, args)
    if args.command == "gui":
        from garmin_optimizer.ui.main_window import launch_gui

        return launch_gui()

    if args.command in {"capture", "validate", "compare", "plan", "bundle"}:
        configuration, bundles, planning = _offline_services(config, redactor)
        if args.command == "capture":
            snapshot = bundles.load_snapshot(Path(args.snapshot))
            bundle_path = bundles.capture(snapshot, args.name, args.description)
            validation = bundles.require_valid(bundle_path)
            print(f"Bundle: {bundle_path}")
            print(f"Integrity: {'valid' if validation.valid else 'invalid'}")
            if args.export_zip:
                print(f"Archive: {bundles.export_archive(bundle_path)}")
            print("Device transport used: No")
            return 0
        if args.command == "validate":
            path = Path(args.path)
            if path.is_dir():
                result = bundles.validate(path)
                print(result.model_dump_json(indent=2))
                if not result.valid:
                    raise BundleValidationError("Bundle validation failed.")
            else:
                loaded = configuration.load(path)
                print(
                    json.dumps(
                        {
                            "valid": True,
                            "schema_version": loaded.schema_version,
                            "profile": redactor.redact_text(loaded.profile.name),
                            "setting_count": len(loaded.settings),
                        },
                        indent=2,
                    )
                )
            return 0
        if args.command == "compare":
            older = bundles.load_configuration(Path(args.older))
            newer = bundles.load_configuration(Path(args.newer))
            comparison = planning.compare(older, newer)
            json_path, markdown_path = planning.save(comparison, "comparison")
            differences = sum(
                item.classification.value != "already_compliant" for item in comparison.operations
            )
            print(f"JSON report: {json_path}")
            print(f"Markdown report: {markdown_path}")
            print(f"Differences: {differences}")
            print("Device transport used: No")
            return 0
        if args.command == "plan":
            desired = bundles.load_configuration(Path(args.configuration))
            overlays = [configuration.load_overlay(Path(item)) for item in args.overlay]
            if overlays:
                resolution = configuration.resolve_overlays(desired, overlays)
                desired = resolution.configuration
                for conflict in resolution.conflicts:
                    print(
                        "Overlay conflict resolved by order: "
                        f"{conflict.setting_id} ({conflict.previous_overlay} -> {conflict.replacing_overlay})"
                    )
            snapshot = bundles.load_snapshot(Path(args.snapshot))
            observed = planning.observed_from_snapshot(snapshot)
            change_plan = planning.plan(desired, observed)
            json_path, markdown_path = planning.save(change_plan)
            print(f"JSON plan: {json_path}")
            print(f"Markdown plan: {markdown_path}")
            print(f"Operations: {len(change_plan.operations)}")
            print("Automatic operations: 0")
            print("Device transport used: No")
            return 0
        if args.bundle_command == "export":
            print(f"Archive: {bundles.export_archive(Path(args.path))}")
            return 0
        if args.bundle_command == "import":
            print(f"Imported bundle: {bundles.import_archive(Path(args.path))}")
            return 0

    adb = AdbService()
    appium = AppiumService(config.appium_url)
    app_discovery = GarminAppDiscoveryService(adb)

    if args.command == "doctor":
        print(f"Python: {platform.python_version()}")
        print(f"Android UI research enabled: {config.android_ui_research_enabled}")
        problems = 0
        try:
            print(f"ADB: {adb.version()}")
            print(f"Devices: {len(adb.list_devices())}")
        except OptimizerError as exc:
            problems += 1
            print(f"ADB: blocked ({redactor.redact_text(str(exc))})")
        try:
            status = appium.check_endpoint()
            print(f"Appium ready: {status['ready']}")
            problems += int(not status["ready"])
        except OptimizerError as exc:
            problems += 1
            print(f"Appium: blocked ({redactor.redact_text(str(exc))})")
        print("Physical write capability: blocked")
        return 1 if problems else 0

    if args.command == "adb" and args.adb_command == "devices":
        for item in adb.list_devices():
            payload = item.model_dump(mode="json")
            if not args.show_serial:
                payload = redactor.redact_data(payload)
            print(json.dumps(payload))
        return 0

    if args.command == "garmin" and args.garmin_command == "detect":
        device = _select_device(adb, args.serial)
        garmin_result = app_discovery.detect_connect(device.serial)
        print(garmin_result.selected.model_dump_json(indent=2) if garmin_result.selected else "{}")
        return 0

    if args.command == "appium" and args.appium_command == "check":
        print(json.dumps(appium.check_endpoint(), indent=2))
        return 0

    if args.command == "audit":
        _require_research_opt_in(args, config)
        ui_discovery = UiDiscoveryService(config.diagnostics_dir, redactor, config.diagnostics_enabled)
        capability_service = CapabilityService(config.manifests_dir, redactor)
        audit_service = ReadOnlyAuditService(
            adb=adb,
            appium=appium,
            app_discovery=app_discovery,
            ui_discovery=ui_discovery,
            capabilities=capability_service,
        )
        audit_result = audit_service.run(args.serial, args.watch or config.target_watch_model)
        snapshot_path = SettingsSnapshotService(config.snapshots_dir, redactor).save_snapshot(audit_result.snapshot)
        manifest_path = capability_service.save(audit_result.manifest)
        report_status, report_path = PocReportService(config.reports_dir, redactor).generate(audit_result.snapshot)
        print(f"Snapshot: {snapshot_path}")
        print(f"Capability manifest: {manifest_path}")
        print(f"Report: {report_path}")
        print(f"Classification: level {report_status.level} ({report_status.summary})")
        return 0

    raise RuntimeError("Unsupported command")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        code = run(args)
    except OptimizerError as exc:
        print(f"ERROR: {RedactionService().redact_text(str(exc))}", file=sys.stderr)
        raise SystemExit(2) from exc
    except Exception as exc:
        print(f"ERROR: {RedactionService().redact_text(str(exc))}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(code)


if __name__ == "__main__":
    main()
