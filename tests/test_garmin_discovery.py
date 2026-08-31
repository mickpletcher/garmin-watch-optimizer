import pytest

from garmin_optimizer.exceptions import GarminConnectNotFoundError
from garmin_optimizer.services.adb_service import AdbService
from garmin_optimizer.services.garmin_app_discovery import GarminAppDiscoveryService


class StubAdb(AdbService):
    def __init__(self, packages: list[str]) -> None:
        super().__init__(adb_path="adb")
        self.packages = packages

    def list_packages(self, serial: str):
        return self.packages

    def resolve_launchable_activity(self, serial: str, package_name: str):
        return "MainActivity"

    def app_version(self, serial: str, package_name: str):
        return "5.0.0"


def test_exact_connect_package_is_required() -> None:
    service = GarminAppDiscoveryService(
        StubAdb(["com.garmin.android.apps.connectmobile", "com.garmin.connectiq"])
    )
    result = service.detect_connect("ABC")
    assert result.selected is not None
    assert result.selected.package_name == "com.garmin.android.apps.connectmobile"
    assert result.selected.confidence == 1.0


def test_connect_iq_is_not_misidentified_as_connect() -> None:
    with pytest.raises(GarminConnectNotFoundError):
        GarminAppDiscoveryService(StubAdb(["com.garmin.connectiq"])).detect_connect("ABC")
