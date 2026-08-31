from __future__ import annotations

from pathlib import Path

from garmin_optimizer.models import SnapshotArtifact
from garmin_optimizer.services.persistence import atomic_write_json, utc_file_stamp
from garmin_optimizer.services.redaction import RedactionService


class SettingsSnapshotService:
    def __init__(self, snapshots_dir: Path, redactor: RedactionService) -> None:
        self.snapshots_dir = snapshots_dir
        self.redactor = redactor

    def save_snapshot(self, snapshot: SnapshotArtifact) -> Path:
        path = self.snapshots_dir / f"snapshot_{utc_file_stamp()}.json"
        payload = snapshot.model_dump(mode="json")
        atomic_write_json(path, self.redactor.redact_data(payload))
        return path

    def diff_snapshots(self, older: SnapshotArtifact, newer: SnapshotArtifact) -> dict[str, list[str]]:
        old_map = {item.id: item for item in older.settings}
        new_map = {item.id: item for item in newer.settings}
        added = [new_map[key].label for key in new_map.keys() - old_map.keys()]
        removed = [old_map[key].label for key in old_map.keys() - new_map.keys()]
        changed = [
            new_map[key].label
            for key in old_map.keys() & new_map.keys()
            if old_map[key].current_value != new_map[key].current_value
        ]
        return {"added": sorted(added), "removed": sorted(removed), "changed": sorted(changed)}
