import json
from pathlib import Path

from garmin_optimizer.models import AndroidDevice, DiscoveredSetting, SnapshotArtifact
from garmin_optimizer.services.redaction import RedactionService
from garmin_optimizer.services.snapshot_service import SettingsSnapshotService


def setting(identifier: str, label: str, value: str) -> DiscoveredSetting:
    return DiscoveredSetting(
        id=identifier,
        screen_path=["A"],
        label=label,
        current_value=value,
        confidence=0.9,
    )


def test_snapshot_diff_save_redaction_and_unique_names(tmp_path: Path) -> None:
    service = SettingsSnapshotService(tmp_path, RedactionService())
    older = SnapshotArtifact(
        host_os="Windows",
        python_version="3.12.0",
        settings=[setting("system.a", "Units", "Statute")],
    )
    newer = SnapshotArtifact(
        host_os="Windows",
        python_version="3.12.0",
        device=AndroidDevice(serial="ABCDEF1234567890", state="device"),
        settings=[
            setting("system.a", "Units", "test.user@example.com"),
            setting("system.b", "Language", "English"),
        ],
    )

    assert service.diff_snapshots(older, newer) == {
        "added": ["Language"],
        "removed": [],
        "changed": ["Units"],
    }
    first = service.save_snapshot(newer)
    second = service.save_snapshot(newer)
    assert first != second
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["device"]["serial"] == "<redacted>"
    assert "example.com" not in first.read_text(encoding="utf-8")
