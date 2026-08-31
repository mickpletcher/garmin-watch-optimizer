from __future__ import annotations

import platform
import sys
from typing import Any

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from garmin_optimizer.config import AppConfig
from garmin_optimizer.logging_utils import setup_logging
from garmin_optimizer.services.adb_service import AdbService
from garmin_optimizer.services.appium_service import AppiumService
from garmin_optimizer.services.capability_service import CapabilityService
from garmin_optimizer.services.garmin_app_discovery import GarminAppDiscoveryService
from garmin_optimizer.services.read_only_audit import ReadOnlyAuditService
from garmin_optimizer.services.redaction import RedactionService
from garmin_optimizer.services.report_service import PocReportService
from garmin_optimizer.services.snapshot_service import SettingsSnapshotService
from garmin_optimizer.services.ui_discovery import UiDiscoveryService
from garmin_optimizer.ui.widgets import StatusLabel
from garmin_optimizer.ui.workers import Worker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig.from_env()
        self.redactor = RedactionService()
        setup_logging(self.config.logs_dir, self.redactor)
        self.adb = AdbService()
        self.appium = AppiumService(self.config.appium_url)
        self.app_discovery = GarminAppDiscoveryService(self.adb)
        self.ui_discovery = UiDiscoveryService(
            self.config.diagnostics_dir,
            self.redactor,
            self.config.diagnostics_enabled,
        )
        self.capabilities = CapabilityService(self.config.manifests_dir, self.redactor)
        self.audit_service = ReadOnlyAuditService(
            self.adb,
            self.appium,
            self.app_discovery,
            self.ui_discovery,
            self.capabilities,
        )
        self.snapshots = SettingsSnapshotService(self.config.snapshots_dir, self.redactor)
        self.reports = PocReportService(self.config.reports_dir, self.redactor)
        self.thread_pool = QThreadPool.globalInstance()

        self.setWindowTitle("Garmin Watch Optimizer Read-Only Research")
        self.resize(1100, 760)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        self.status_policy = StatusLabel("Unknown")
        self.status_environment = StatusLabel("Unknown")
        self.status_audit = StatusLabel("Not run")
        for title, status in [
            ("Android UI research policy", self.status_policy),
            ("Environment", self.status_environment),
            ("Read-only audit", self.status_audit),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(title))
            row.addWidget(status)
            layout.addLayout(row)

        self.btn_doctor = QPushButton("Run Environment Check")
        self.btn_doctor.clicked.connect(self.run_doctor)
        layout.addWidget(self.btn_doctor)
        self.btn_audit = QPushButton("Run Read-Only Audit")
        self.btn_audit.clicked.connect(self.run_audit)
        self.btn_audit.setEnabled(self.config.android_ui_research_enabled)
        layout.addWidget(self.btn_audit)
        self.status_policy.set_status(
            "Enabled" if self.config.android_ui_research_enabled else "Disabled",
            "research only; physical writes blocked",
        )

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Screen", "Setting", "Current Value", "Risk", "Access"])
        layout.addWidget(self.table)
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        layout.addWidget(self.event_log)
        self.setCentralWidget(root)

    def _run_async(self, fn, on_success) -> None:
        self.btn_doctor.setEnabled(False)
        self.btn_audit.setEnabled(False)
        worker = Worker(fn)
        worker.signals.failed.connect(self._on_error)
        worker.signals.finished.connect(lambda result: self._on_success(result, on_success))
        self.thread_pool.start(worker)

    def _restore_buttons(self) -> None:
        self.btn_doctor.setEnabled(True)
        self.btn_audit.setEnabled(self.config.android_ui_research_enabled)

    def _on_error(self, message: str) -> None:
        safe_message = self.redactor.redact_text(message)
        self.event_log.append(f"ERROR: {safe_message}")
        QMessageBox.critical(self, "Operation failed", safe_message)
        self._restore_buttons()

    def _on_success(self, result: Any, callback) -> None:
        callback(result)
        self._restore_buttons()

    def run_doctor(self) -> None:
        def job() -> dict[str, Any]:
            return {
                "python": platform.python_version(),
                "adb": self.adb.version(),
                "devices": len(self.adb.list_devices()),
                "appium": self.appium.check_endpoint(),
            }

        def done(result: dict[str, Any]) -> None:
            ready = bool(result["appium"]["ready"])
            self.status_environment.set_status(
                "Ready" if ready else "Blocked",
                f"Python {result['python']}; {result['devices']} Android device(s)",
            )
            self.event_log.append("Environment check completed. Physical writes remain blocked.")

        self._run_async(job, done)

    def run_audit(self) -> None:
        def job() -> dict[str, Any]:
            result = self.audit_service.run(None, self.config.target_watch_model)
            snapshot_path = self.snapshots.save_snapshot(result.snapshot)
            manifest_path = self.capabilities.save(result.manifest)
            status, report_path = self.reports.generate(result.snapshot)
            return {
                "snapshot": result.snapshot,
                "snapshot_path": snapshot_path,
                "manifest_path": manifest_path,
                "report_path": report_path,
                "status": status,
            }

        def done(result: dict[str, Any]) -> None:
            snapshot = result["snapshot"]
            self.table.setRowCount(0)
            for setting in snapshot.settings:
                index = self.table.rowCount()
                self.table.insertRow(index)
                self.table.setItem(index, 0, QTableWidgetItem(" > ".join(setting.screen_path)))
                self.table.setItem(index, 1, QTableWidgetItem(setting.label))
                self.table.setItem(index, 2, QTableWidgetItem(setting.current_value or ""))
                self.table.setItem(index, 3, QTableWidgetItem(setting.risk_level.value))
                self.table.setItem(index, 4, QTableWidgetItem("Read only"))
            self.status_audit.set_status("Complete", result["status"].summary)
            self.event_log.append(
                f"Saved snapshot {result['snapshot_path']}, manifest {result['manifest_path']}, "
                f"and report {result['report_path']}."
            )

        self._run_async(job, done)


def launch_gui() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
