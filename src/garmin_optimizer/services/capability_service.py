from __future__ import annotations

from pathlib import Path

from garmin_optimizer.models import (
    Capability,
    CapabilityManifest,
    CapabilitySupport,
    DiscoveredSetting,
    GarminApp,
    GarminDevice,
    RiskLevel,
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
                support=CapabilitySupport.OBSERVED,
                evidence=["Exact Garmin Connect package detected through ADB."],
            ),
            Capability(
                id="watch.identity",
                title="Watch model and firmware identity",
                support=CapabilitySupport.OBSERVED if device.model_hint else CapabilitySupport.UNKNOWN,
                evidence=["Read from visible Garmin Connect device UI."],
            ),
            Capability(
                id="settings.visible_screen_capture",
                title="Visible settings screen capture",
                support=CapabilitySupport.OBSERVED if settings else CapabilitySupport.UNKNOWN,
                evidence=[f"Observed {len(settings)} structured setting rows."],
            ),
            Capability(
                id="settings.automatic_write",
                title="Automatic watch setting writes",
                support=CapabilitySupport.UNAVAILABLE,
                access="blocked",
                risk_level=RiskLevel.DESTRUCTIVE,
                evidence=["No production write adapter exists. Simulation cannot access Appium or ADB."],
            ),
        ]
        capabilities.extend(
            Capability(
                id=f"setting.{setting.id}",
                title=setting.label,
                support=CapabilitySupport.OBSERVED,
                access="read_only",
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
