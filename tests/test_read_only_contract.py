from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path

import pytest

from garmin_optimizer.exceptions import AppiumUnavailableError, GarminConnectNotAuthenticatedError
from garmin_optimizer.models import AndroidDevice, AuthenticationState
from garmin_optimizer.services.adb_service import AdbService
from garmin_optimizer.services.appium_service import AppiumService
from garmin_optimizer.services.capability_service import CapabilityService
from garmin_optimizer.services.garmin_app_discovery import GarminAppDiscoveryService
from garmin_optimizer.services.read_only_audit import ReadOnlyAuditService
from garmin_optimizer.services.redaction import RedactionService
from garmin_optimizer.services.ui_discovery import UiDiscoveryService


class FakeAdb(AdbService):
    def __init__(self) -> None:
        super().__init__(adb_path="adb")

    def list_devices(self):
        return [AndroidDevice(serial="ABC123", state="device", model="Pixel")]

    def enrich_device(self, device):
        return device.model_copy(update={"manufacturer": "Google", "android_version": "16"})

    def list_packages(self, serial: str):
        return ["com.garmin.android.apps.connectmobile", "com.garmin.connectiq"]

    def resolve_launchable_activity(self, serial: str, package_name: str):
        return "MainActivity"

    def app_version(self, serial: str, package_name: str):
        return "5.0.0"

    def version(self):
        return "Android Debug Bridge 1.0.41"


class FakeElement:
    def __init__(self, callback) -> None:
        self.callback = callback

    def click(self) -> None:
        self.callback()


class FakeAppium:
    def __init__(self, initial: str = "home") -> None:
        self.state = initial
        self.closed = False
        self.pages = {
            "home": "authenticated_home.xml",
            "sign_in": "unexpected_screen.xml",
            "more": "more_screen.xml",
            "devices": "devices_screen.xml",
            "device": "device_screen.xml",
            "settings": "settings_screen.xml",
        }
        self.transitions = {
            ("home", "More"): "more",
            ("more", "Garmin Devices"): "devices",
            ("devices", "Enduro 2"): "device",
            ("device", "Device Settings"): "settings",
        }

    def check_endpoint(self):
        return {"ready": True, "endpoint": "http://127.0.0.1:4723"}

    @contextmanager
    def session(self, serial: str, package_name: str, activity_name: str | None = None):
        assert serial == "ABC123"
        assert package_name == "com.garmin.android.apps.connectmobile"
        try:
            yield object()
        finally:
            self.closed = True

    def activate_app(self, package_name: str) -> None:
        assert package_name == "com.garmin.android.apps.connectmobile"

    def page_source(self) -> str:
        return Path("tests/fixtures", self.pages[self.state]).read_text(encoding="utf-8")

    def find_elements(self, by: str, selector: str):
        match = re.search(r'(?:text|description)\("(.+)"\)', selector)
        label = match.group(1) if match else ""
        destination = self.transitions.get((self.state, label))
        if destination is None:
            return []
        return [FakeElement(lambda: setattr(self, "state", destination))]


def make_service(tmp_path: Path, appium: FakeAppium) -> ReadOnlyAuditService:
    redactor = RedactionService()
    adb = FakeAdb()
    return ReadOnlyAuditService(
        adb=adb,
        appium=appium,
        app_discovery=GarminAppDiscoveryService(adb),
        ui_discovery=UiDiscoveryService(tmp_path / "diagnostics", redactor),
        capabilities=CapabilityService(tmp_path / "manifests", redactor),
    )


def test_fake_device_contract_covers_read_only_vertical_slice(tmp_path: Path) -> None:
    appium = FakeAppium()
    result = make_service(tmp_path, appium).run("ABC123", "Enduro 2")

    assert appium.closed
    assert result.snapshot.authentication_state is AuthenticationState.AUTHENTICATED
    assert result.snapshot.garmin_device is not None
    assert result.snapshot.garmin_device.firmware_version == "18.16"
    assert len(result.snapshot.settings) == 3
    assert result.snapshot.screens_reached[-1] == "Device Settings"
    write = next(item for item in result.manifest.capabilities if item.id == "settings.automatic_write")
    assert write.access == "blocked"


def test_authentication_failure_closes_session_without_navigation(tmp_path: Path) -> None:
    appium = FakeAppium(initial="sign_in")
    with pytest.raises(GarminConnectNotAuthenticatedError):
        make_service(tmp_path, appium).run("ABC123", "Enduro 2")
    assert appium.closed
    assert appium.state == "sign_in"


def test_remote_appium_endpoint_is_blocked() -> None:
    with pytest.raises(AppiumUnavailableError):
        AppiumService("https://example.com:4723")
