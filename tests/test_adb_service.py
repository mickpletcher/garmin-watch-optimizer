import pytest

from garmin_optimizer.exceptions import AndroidDeviceUnauthorizedError, NoAndroidDeviceError
from garmin_optimizer.models import AndroidDevice
from garmin_optimizer.services.adb_service import AdbService, CommandResult


class FakeAdb(AdbService):
    def __init__(self, output: str) -> None:
        super().__init__(adb_path="adb")
        self._output = output

    def run(self, args, serial=None, timeout_seconds=None):
        return CommandResult(stdout=self._output, stderr="", returncode=0)


def test_list_devices_parses_states() -> None:
    output = """List of devices attached
ABC123 device model:Pixel_8 device:husky transport_id:1
DEF456 unauthorized transport_id:2
"""
    service = FakeAdb(output)
    devices = service.list_devices()

    assert devices[0] == AndroidDevice(serial="ABC123", state="device", manufacturer="husky", model="Pixel_8")
    assert devices[1].state == "unauthorized"
    assert service.select_device(devices, "ABC123").serial == "ABC123"


def test_explicit_serial_must_exist_and_be_ready() -> None:
    service = FakeAdb("")
    with pytest.raises(NoAndroidDeviceError):
        service.select_device([], "missing")
    with pytest.raises(AndroidDeviceUnauthorizedError):
        service.select_device([AndroidDevice(serial="ABC", state="unauthorized")], "ABC")
