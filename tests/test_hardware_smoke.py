import os

import pytest

from garmin_optimizer.config import AppConfig
from garmin_optimizer.services.adb_service import AdbService
from garmin_optimizer.services.appium_service import AppiumService
from garmin_optimizer.services.garmin_app_discovery import GarminAppDiscoveryService


@pytest.mark.hardware
def test_read_only_hardware_prerequisites() -> None:
    if os.getenv("GARMIN_OPT_HARDWARE_TESTS") != "1":
        pytest.skip("Set GARMIN_OPT_HARDWARE_TESTS=1 to run the opt-in read-only hardware smoke test.")
    config = AppConfig.from_env()
    adb = AdbService()
    device = adb.select_device(adb.list_devices())
    app = GarminAppDiscoveryService(adb).detect_connect(device.serial).selected
    assert app is not None
    assert AppiumService(config.appium_url).check_endpoint()["ready"] is True
