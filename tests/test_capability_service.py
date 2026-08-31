import json
from pathlib import Path

from garmin_optimizer.models import CapabilitySupport, DiscoveredSetting, GarminApp, GarminDevice, RiskLevel
from garmin_optimizer.services.capability_service import CapabilityService
from garmin_optimizer.services.redaction import RedactionService


def test_manifest_marks_write_capability_unavailable(tmp_path: Path) -> None:
    service = CapabilityService(tmp_path, RedactionService())
    manifest = service.build(
        GarminApp(package_name="com.garmin.android.apps.connectmobile", app_version="5.0"),
        GarminDevice(display_name="Enduro 2", model_hint="Enduro 2", firmware_version="18.16"),
        [
            DiscoveredSetting(
                id="units",
                screen_path=["Settings"],
                label="Units",
                current_value="Metric",
                confidence=0.9,
                risk_level=RiskLevel.LOW,
            )
        ],
    )
    write = next(item for item in manifest.capabilities if item.id == "settings.automatic_write")
    assert write.support is CapabilitySupport.UNAVAILABLE
    assert write.access == "blocked"
    path = service.save(manifest)
    assert json.loads(path.read_text(encoding="utf-8"))["research_only"] is True
