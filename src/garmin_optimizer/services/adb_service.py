from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass

from garmin_optimizer.exceptions import (
    AdbNotFoundError,
    AndroidDeviceUnauthorizedError,
    MultipleAndroidDevicesError,
    NoAndroidDeviceError,
)
from garmin_optimizer.models import AndroidDevice

LOGGER = logging.getLogger(__name__)


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


class AdbService:
    def __init__(self, adb_path: str | None = None, timeout_seconds: int = 15) -> None:
        self._adb_path = adb_path
        self.timeout_seconds = timeout_seconds

    @property
    def adb_path(self) -> str:
        if self._adb_path:
            return self._adb_path
        discovered = shutil.which("adb")
        if not discovered:
            raise AdbNotFoundError(
                "ADB executable was not found. Install Android Platform Tools and add adb to PATH."
            )
        self._adb_path = discovered
        return discovered

    def run(self, args: list[str], serial: str | None = None, timeout_seconds: int | None = None) -> CommandResult:
        command = [self.adb_path]
        if serial:
            command.extend(["-s", serial])
        command.extend(args)
        timeout = timeout_seconds or self.timeout_seconds
        LOGGER.debug("Running adb command: %s", command)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
            returncode=completed.returncode,
        )

    def version(self) -> str:
        result = self.run(["version"])
        if result.returncode != 0:
            raise AdbNotFoundError(f"Failed to run adb version: {result.stderr}")
        line = result.stdout.splitlines()[0] if result.stdout else "unknown"
        return line

    def list_devices(self) -> list[AndroidDevice]:
        result = self.run(["devices", "-l"])
        if result.returncode != 0:
            raise NoAndroidDeviceError(f"Unable to list adb devices: {result.stderr}")

        devices: list[AndroidDevice] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices attached"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            state = parts[1]
            model = None
            manufacturer = None
            model_match = re.search(r"model:([^\s]+)", line)
            if model_match:
                model = model_match.group(1)
            manufacturer_match = re.search(r"device:([^\s]+)", line)
            if manufacturer_match:
                manufacturer = manufacturer_match.group(1)
            devices.append(
                AndroidDevice(
                    serial=serial,
                    state=state,
                    manufacturer=manufacturer,
                    model=model,
                )
            )
        return devices

    def choose_single_device(self, devices: list[AndroidDevice]) -> AndroidDevice:
        active = [d for d in devices if d.state == "device"]
        unauthorized = [d for d in devices if d.state == "unauthorized"]
        if unauthorized and not active:
            raise AndroidDeviceUnauthorizedError(
                "Android device is unauthorized. Accept the USB debugging prompt on the phone."
            )
        if not active:
            raise NoAndroidDeviceError("No authorized Android devices found.")
        if len(active) > 1:
            raise MultipleAndroidDevicesError(
                "Multiple authorized Android devices found. Choose a device in the UI or CLI option."
            )
        return active[0]

    def select_device(self, devices: list[AndroidDevice], serial: str | None = None) -> AndroidDevice:
        if serial is None:
            return self.choose_single_device(devices)
        matches = [device for device in devices if device.serial == serial]
        if not matches:
            raise NoAndroidDeviceError(f"ADB device '{serial}' was not found.")
        selected = matches[0]
        if selected.state == "unauthorized":
            raise AndroidDeviceUnauthorizedError(
                "Android device is unauthorized. Accept the USB debugging prompt on the phone."
            )
        if selected.state != "device":
            raise NoAndroidDeviceError(f"ADB device '{serial}' is not ready. Current state: {selected.state}.")
        return selected

    def enrich_device(self, device: AndroidDevice) -> AndroidDevice:
        serial = device.serial
        manufacturer = self.getprop(serial, "ro.product.manufacturer")
        model = self.getprop(serial, "ro.product.model")
        android_version = self.getprop(serial, "ro.build.version.release")
        return AndroidDevice(
            serial=serial,
            state=device.state,
            manufacturer=manufacturer or device.manufacturer,
            model=model or device.model,
            android_version=android_version,
        )

    def getprop(self, serial: str, prop: str) -> str | None:
        result = self.run(["shell", "getprop", prop], serial=serial)
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None

    def list_packages(self, serial: str) -> list[str]:
        result = self.run(["shell", "pm", "list", "packages"], serial=serial, timeout_seconds=30)
        if result.returncode != 0:
            raise NoAndroidDeviceError(f"Unable to query packages: {result.stderr}")
        packages: list[str] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                packages.append(line.replace("package:", "", 1))
        return packages

    def resolve_launchable_activity(self, serial: str, package_name: str) -> str | None:
        # cmd package resolve-activity returns the currently exported launch activity.
        result = self.run(
            [
                "shell",
                "cmd",
                "package",
                "resolve-activity",
                "--brief",
                package_name,
            ],
            serial=serial,
        )
        if result.returncode != 0:
            return None
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            return None
        last = lines[-1]
        if "/" not in last:
            return None
        return last.split("/", 1)[1]

    def app_version(self, serial: str, package_name: str) -> str | None:
        result = self.run(["shell", "dumpsys", "package", package_name], serial=serial, timeout_seconds=30)
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("versionName="):
                return line.split("=", 1)[1]
        return None
