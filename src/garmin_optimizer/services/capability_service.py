from __future__ import annotations

from pathlib import Path
from typing import cast

from pydantic import JsonValue

from garmin_optimizer.models import (
    Capability,
    CapabilityManifest,
    DiscoveredSetting,
    GarminApp,
    GarminDevice,
    ReadSupport,
    RiskLevel,
    WriteSupport,
)
from garmin_optimizer.services.persistence import atomic_write_json, utc_file_stamp
from garmin_optimizer.services.redaction import RedactionService


class CapabilityService:
    def __init__(self, manifests_dir: Path, redactor: RedactionService) -> None:
        self.manifests_dir = manifests_dir
        self.redactor = redactor

    def build(
        self,
        app: GarminApp,
        device: GarminDevice,
        settings: list[DiscoveredSetting],
    ) -> CapabilityManifest:
        capabilities = [
            Capability(
                id="transport.android_ui_research",
                title="Local Android UI research transport",
                description="Opt-in, loopback-only accessibility inspection after manual sign-in.",
                read_support=ReadSupport.PARTIAL,
                write_support=WriteSupport.READ_ONLY,
                adapter="android_ui_research",
                transport="adb_appium_loopback",
                supported_models=[device.model_hint or device.display_name],
                firmware_constraints=[device.firmware_version] if device.firmware_version else [],
                risk_level=RiskLevel.HIGH,
                evidence=["Exact Garmin Connect package detected through ADB."],
            ),
            Capability(
                id="watch.identity",
                title="Watch model and firmware identity",
                description="Visible watch model and firmware metadata.",
                read_support=ReadSupport.FULL if device.model_hint else ReadSupport.UNKNOWN,
                write_support=WriteSupport.UNSUPPORTED,
                adapter="android_ui_research",
                transport="adb_appium_loopback",
                supported_models=[device.model_hint or device.display_name],
                firmware_constraints=[device.firmware_version] if device.firmware_version else [],
                risk_level=RiskLevel.LOW,
                evidence=["Read from visible Garmin Connect device UI."],
            ),
            Capability(
                id="settings.visible_screen_capture",
                title="Visible settings screen capture",
                description="Structured rows from the single visible device settings root.",
                read_support=ReadSupport.PARTIAL if settings else ReadSupport.UNKNOWN,
                write_support=WriteSupport.READ_ONLY,
                adapter="android_ui_research",
                transport="adb_appium_loopback",
                supported_models=[device.model_hint or device.display_name],
                firmware_constraints=[device.firmware_version] if device.firmware_version else [],
                risk_level=RiskLevel.HIGH,
                evidence=[f"Observed {len(settings)} structured setting rows."],
            ),
            Capability(
                id="settings.automatic_write",
                title="Automatic watch setting writes",
                description="Physical setting mutation is not implemented or authorized.",
                read_support=ReadSupport.NONE,
                write_support=WriteSupport.UNSUPPORTED,
                adapter="none",
                transport="none",
                supported_models=[device.model_hint or device.display_name],
                firmware_constraints=[device.firmware_version] if device.firmware_version else [],
                risk_level=RiskLevel.DESTRUCTIVE,
                evidence=["No production write adapter exists. Simulation cannot access Appium or ADB."],
            ),
        ]
        capabilities.extend(
            Capability(
                id=f"setting.{setting.id}",
                title=setting.label,
                description="Observed current value from a visible structured settings row.",
                read_support=ReadSupport.FULL,
                write_support=WriteSupport.READ_ONLY,
                adapter="android_ui_research",
                transport="adb_appium_loopback",
                supported_values=cast(list[JsonValue], setting.selectable_values),
                supported_models=[device.model_hint or device.display_name],
                firmware_constraints=[device.firmware_version] if device.firmware_version else [],
                risk_level=setting.risk_level,
                evidence=["Observed on the current visible device settings screen."],
            )
            for setting in settings
        )
        return CapabilityManifest(
            app_package=app.package_name,
            app_version=app.app_version,
            device_model=device.model_hint or device.display_name,
            firmware_version=device.firmware_version,
            capabilities=capabilities,
        )

    def save(self, manifest: CapabilityManifest) -> Path:
        path = self.manifests_dir / f"capability_manifest_{utc_file_stamp()}.json"
        payload = self.redactor.redact_data(manifest.model_dump(mode="json"))
        atomic_write_json(path, payload)
        return path
