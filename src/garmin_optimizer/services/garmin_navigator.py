from __future__ import annotations

import re
from dataclasses import dataclass

from appium.webdriver.common.appiumby import AppiumBy

from garmin_optimizer.exceptions import GarminDeviceNotFoundError, NavigationMismatchError
from garmin_optimizer.models import GarminDevice
from garmin_optimizer.services.appium_service import AppiumService
from garmin_optimizer.services.ui_discovery import UiDiscoveryService


@dataclass
class NavigationTrace:
    screens: list[str]


class GarminConnectNavigator:
    DEVICE_PATTERN = re.compile(r"\b(enduro|fenix|forerunner|epix|instinct|venu|vivoactive)\b", re.I)

    def __init__(
        self,
        appium_service: AppiumService,
        ui_discovery: UiDiscoveryService,
        package_name: str,
    ) -> None:
        self.appium_service = appium_service
        self.ui_discovery = ui_discovery
        self.package_name = package_name
        self.trace = NavigationTrace(screens=[])

    def open_app(self) -> None:
        self.appium_service.activate_app(self.package_name)
        self.trace.screens.append("Garmin Connect Home")

    def open_devices(self) -> None:
        texts = self.ui_discovery.visible_texts(self.appium_service.page_source())
        if not self._contains(texts, "Garmin Devices"):
            self._click_exact(["More"])
        self._click_exact(["Garmin Devices", "Devices"])
        self.trace.screens.append("Garmin Devices")

    def list_devices(self) -> list[GarminDevice]:
        texts = self.ui_discovery.visible_texts(self.appium_service.page_source())
        connected = next((value for value in texts if value.casefold() in {"connected", "syncing"}), None)
        devices: list[GarminDevice] = []
        for text in texts:
            match = self.DEVICE_PATTERN.search(text)
            if match and all(existing.display_name.casefold() != text.casefold() for existing in devices):
                devices.append(
                    GarminDevice(
                        display_name=text,
                        model_hint=self._model_hint(text),
                        connected_state=connected,
                    )
                )
        if not devices:
            raise GarminDeviceNotFoundError("No supported Garmin watch identity was visible on the devices screen.")
        return devices

    def choose_device(self, devices: list[GarminDevice], target_name: str) -> GarminDevice:
        exact = [device for device in devices if device.display_name.casefold() == target_name.casefold()]
        if exact:
            return exact[0]
        partial = [device for device in devices if target_name.casefold() in device.display_name.casefold()]
        if len(partial) == 1:
            return partial[0]
        visible = ", ".join(device.display_name for device in devices)
        raise GarminDeviceNotFoundError(f"Target watch '{target_name}' was not uniquely identified. Visible: {visible}")

    def open_device(self, device: GarminDevice) -> None:
        self._click_exact([device.display_name])
        self.trace.screens.append(f"Device {device.model_hint or device.display_name}")

    def read_device_identity(self, selected: GarminDevice) -> GarminDevice:
        texts = self.ui_discovery.visible_texts(self.appium_service.page_source())
        firmware = self._value_after(texts, {"software version", "firmware version", "software"})
        connected = next((value for value in texts if value.casefold() in {"connected", "syncing"}), None)
        return selected.model_copy(
            update={
                "firmware_version": firmware,
                "connected_state": connected or selected.connected_state,
            }
        )

    def open_settings_root(self) -> None:
        self._click_exact(["Device Settings", "Settings", "System"])
        self.trace.screens.append("Device Settings")

    def _click_exact(self, labels: list[str]) -> None:
        for label in labels:
            escaped = label.replace("\\", "\\\\").replace('"', '\\"')
            selectors = [
                f'new UiSelector().text("{escaped}")',
                f'new UiSelector().description("{escaped}")',
            ]
            for selector in selectors:
                elements = self.appium_service.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, selector)
                if elements:
                    elements[0].click()
                    return
        raise NavigationMismatchError(f"Expected one of these controls: {', '.join(labels)}")

    def _contains(self, values: list[str], target: str) -> bool:
        return any(value.casefold() == target.casefold() for value in values)

    def _value_after(self, values: list[str], labels: set[str]) -> str | None:
        for index, value in enumerate(values[:-1]):
            if value.casefold() in labels:
                return values[index + 1]
        return None

    def _model_hint(self, display_name: str) -> str:
        known_models = {
            "enduro 2": "Enduro 2",
            "enduro": "Enduro",
            "fenix": "fenix",
            "forerunner": "Forerunner",
            "epix": "epix",
            "instinct": "Instinct",
            "venu": "Venu",
            "vivoactive": "vivoactive",
        }
        lowered = display_name.casefold()
        return next((canonical for term, canonical in known_models.items() if term in lowered), "Unknown Garmin watch")
