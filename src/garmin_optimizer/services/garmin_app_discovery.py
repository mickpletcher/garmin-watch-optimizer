from __future__ import annotations

from dataclasses import dataclass

from garmin_optimizer.exceptions import GarminConnectNotFoundError
from garmin_optimizer.models import GarminApp
from garmin_optimizer.services.adb_service import AdbService


@dataclass
class GarminDiscoveryResult:
    candidates: list[GarminApp]
    selected: GarminApp | None


class GarminAppDiscoveryService:
    CONNECT_PACKAGE = "com.garmin.android.apps.connectmobile"

    def __init__(self, adb_service: AdbService) -> None:
        self.adb_service = adb_service

    def detect_candidates(self, serial: str) -> list[GarminApp]:
        packages = set(self.adb_service.list_packages(serial))
        if self.CONNECT_PACKAGE not in packages:
            return []
        package_name = self.CONNECT_PACKAGE
        return [
            GarminApp(
                package_name=package_name,
                activity_name=self.adb_service.resolve_launchable_activity(serial, package_name),
                app_version=self.adb_service.app_version(serial, package_name),
                confidence=1.0,
            )
        ]

    def detect_connect(self, serial: str) -> GarminDiscoveryResult:
        candidates = self.detect_candidates(serial)
        if not candidates:
            raise GarminConnectNotFoundError(
                f"Required Garmin Connect package '{self.CONNECT_PACKAGE}' was not found. Connect IQ is not accepted."
            )
        return GarminDiscoveryResult(candidates=candidates, selected=candidates[0])
