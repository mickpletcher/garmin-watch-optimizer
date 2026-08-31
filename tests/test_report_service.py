import json
from pathlib import Path

from garmin_optimizer.models import (
    AndroidDevice,
    AuthenticationState,
    DiscoveredSetting,
    GarminApp,
    GarminDevice,
    SnapshotArtifact,
)
from garmin_optimizer.services.redaction import RedactionService
from garmin_optimizer.services.report_service import PocReportService


def test_report_is_sanitized_and_never_claims_a_write(tmp_path: Path) -> None:
    snapshot = SnapshotArtifact(
        host_os="Windows",
        python_version="3.12",
        adb_version="Android Debug Bridge",
        appium_status="ready",
        authentication_state=AuthenticationState.AUTHENTICATED,
        device=AndroidDevice(serial="ABCDEF1234567890", state="device"),
        garmin_app=GarminApp(package_name="com.garmin.android.apps.connectmobile", app_version="5.0"),
        garmin_device=GarminDevice(display_name="Enduro 2", model_hint="Enduro 2", firmware_version="18.16"),
        screens_reached=["Garmin Devices", "Device Settings"],
        settings=[
            DiscoveredSetting(
                id="system.units",
                screen_path=["Settings"],
                label="Units",
                current_value="test.user@example.com",
                confidence=0.9,
            )
        ],
    )
    status, markdown = PocReportService(tmp_path, RedactionService()).generate(snapshot)
    json_report = next(tmp_path.glob("*.json"))
    combined = markdown.read_text(encoding="utf-8") + json_report.read_text(encoding="utf-8")

    assert status.level == 2
    assert "ABCDEF1234567890" not in combined
    assert "test.user@example.com" not in combined
    assert "Automatic write capability: blocked" in combined
    assert json.loads(json_report.read_text(encoding="utf-8"))["simulation"] is None
