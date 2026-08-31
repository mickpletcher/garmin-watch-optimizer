from __future__ import annotations

from pathlib import Path

from garmin_optimizer.models import AuthenticationState, PocStatus, SnapshotArtifact, WriteSimulationTransaction
from garmin_optimizer.services.persistence import atomic_write_json, atomic_write_text, utc_file_stamp
from garmin_optimizer.services.redaction import RedactionService


class PocReportService:
    def __init__(self, reports_dir: Path, redactor: RedactionService) -> None:
        self.reports_dir = reports_dir
        self.redactor = redactor

    def generate(
        self,
        snapshot: SnapshotArtifact,
        simulation: WriteSimulationTransaction | None = None,
    ) -> tuple[PocStatus, Path]:
        status = self._classify(snapshot)
        base = self.reports_dir / f"read_only_report_{utc_file_stamp()}"
        markdown_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")
        sanitized = self.redactor.redact_data(snapshot.model_dump(mode="json"))
        device = sanitized.get("device") or {}
        garmin_device = sanitized.get("garmin_device") or {}
        app = sanitized.get("garmin_app") or {}
        lines = [
            "# Garmin Watch Optimizer Read-Only Research Report",
            "",
            "> Android UI research is local, opt-in, and read only. This report does not prove a device write.",
            "",
            "## Environment",
            f"- Host: {sanitized['host_os']}",
            f"- Python: {sanitized['python_version']}",
            f"- ADB: {sanitized.get('adb_version') or 'unknown'}",
            f"- Appium: {sanitized.get('appium_status') or 'unknown'}",
            f"- Android device serial: {device.get('serial', 'not connected')}",
            "",
            "## Garmin",
            f"- Package: {app.get('package_name', 'not detected')}",
            f"- App version: {app.get('app_version') or 'unknown'}",
            f"- Authentication: {sanitized.get('authentication_state', 'unknown')}",
            f"- Watch model: {garmin_device.get('model_hint') or 'not detected'}",
            f"- Firmware: {garmin_device.get('firmware_version') or 'unknown'}",
            "",
            "## Discovery",
            f"- Screens reached: {', '.join(sanitized.get('screens_reached', [])) or 'none'}",
            f"- Structured settings observed: {len(sanitized.get('settings', []))}",
            "- Automatic write capability: blocked",
            "",
            "## Simulation",
            f"- Run: {'Yes' if simulation else 'No'}",
        ]
        if simulation:
            simulation_payload = self.redactor.redact_data(simulation.model_dump(mode="json"))
            lines.extend(
                [
                    f"- Outcome: {simulation_payload['outcome']}",
                    f"- Restoration verified: {simulation_payload['restore_verified']}",
                    "- Device transport used: No",
                ]
            )
        lines.extend(["", "## Classification", f"Level {status.level}: {status.summary}", "", "## Warnings"])
        warnings = sanitized.get("warnings", [])
        lines.extend([f"- {warning}" for warning in warnings] or ["- none"])
        atomic_write_text(markdown_path, "\n".join(lines) + "\n")
        atomic_write_json(
            json_path,
            {
                "status": status.model_dump(mode="json"),
                "snapshot": sanitized,
                "simulation": self.redactor.redact_data(simulation.model_dump(mode="json")) if simulation else None,
            },
        )
        return status, markdown_path

    def _classify(self, snapshot: SnapshotArtifact) -> PocStatus:
        if not snapshot.device:
            return PocStatus(level=0, summary="Environment blocked")
        if not snapshot.garmin_app:
            return PocStatus(level=1, summary="Android ready but exact Garmin Connect package not confirmed")
        if snapshot.authentication_state is not AuthenticationState.AUTHENTICATED:
            return PocStatus(level=1, summary="Garmin Connect authentication not confirmed")
        if not snapshot.garmin_device or not snapshot.settings:
            return PocStatus(level=1, summary="Garmin Connect read-only control proven")
        return PocStatus(level=2, summary="Read-only watch identity and visible settings capture proven")
