from __future__ import annotations

import platform
from dataclasses import dataclass

from garmin_optimizer.exceptions import AppiumUnavailableError, GarminConnectNotAuthenticatedError
from garmin_optimizer.models import AuthenticationState, CapabilityManifest, SnapshotArtifact
from garmin_optimizer.services.adb_service import AdbService
from garmin_optimizer.services.appium_service import AppiumService
from garmin_optimizer.services.capability_service import CapabilityService
from garmin_optimizer.services.garmin_app_discovery import GarminAppDiscoveryService
from garmin_optimizer.services.garmin_navigator import GarminConnectNavigator
from garmin_optimizer.services.ui_discovery import UiDiscoveryService


@dataclass
class ReadOnlyAuditResult:
    snapshot: SnapshotArtifact
    manifest: CapabilityManifest


class ReadOnlyAuditService:
    def __init__(
        self,
        adb: AdbService,
        appium: AppiumService,
        app_discovery: GarminAppDiscoveryService,
        ui_discovery: UiDiscoveryService,
        capabilities: CapabilityService,
    ) -> None:
        self.adb = adb
        self.appium = appium
        self.app_discovery = app_discovery
        self.ui_discovery = ui_discovery
        self.capabilities = capabilities

    def run(self, serial: str | None, target_watch: str) -> ReadOnlyAuditResult:
        android_device = self.adb.select_device(self.adb.list_devices(), serial)
        android_device = self.adb.enrich_device(android_device)
        app_result = self.app_discovery.detect_connect(android_device.serial)
        app = app_result.selected
        if app is None:
            raise AppiumUnavailableError("Exact Garmin Connect package selection failed.")
        appium_status = self.appium.check_endpoint()
        if not appium_status["ready"]:
            raise AppiumUnavailableError("Local Appium server reported that it is not ready.")

        with self.appium.session(android_device.serial, app.package_name, app.activity_name):
            navigator = GarminConnectNavigator(self.appium, self.ui_discovery, app.package_name)
            navigator.open_app()
            authentication = self.ui_discovery.detect_authentication_state(self.appium.page_source())
            if authentication is AuthenticationState.SIGN_IN_REQUIRED:
                raise GarminConnectNotAuthenticatedError(
                    "Garmin Connect requires sign-in. Sign in manually in Garmin Connect, then retry."
                )
            if authentication is not AuthenticationState.AUTHENTICATED:
                raise GarminConnectNotAuthenticatedError(
                    "Garmin Connect authentication state could not be confirmed. No navigation was attempted."
                )

            navigator.open_devices()
            selected = navigator.choose_device(navigator.list_devices(), target_watch)
            navigator.open_device(selected)
            garmin_device = navigator.read_device_identity(selected)
            navigator.open_settings_root()
            settings_source = self.appium.page_source()
            settings = self.ui_discovery.parse_page_source(settings_source, navigator.trace.screens.copy())
            self.ui_discovery.dump_sanitized_xml(settings_source, "read_only_audit")

        manifest = self.capabilities.build(app, garmin_device, settings)
        snapshot = SnapshotArtifact(
            host_os=platform.platform(),
            python_version=platform.python_version(),
            adb_version=self.adb.version(),
            appium_status="ready",
            authentication_state=authentication,
            device=android_device,
            garmin_app=app,
            garmin_device=garmin_device,
            capability_manifest=manifest,
            screens_reached=navigator.trace.screens,
            settings=settings,
            warnings=[
                "Android UI research is opt-in and not confirmed by Garmin as an authorized integration.",
                "Only the visible settings screen was captured. No physical write path exists.",
            ],
        )
        return ReadOnlyAuditResult(snapshot=snapshot, manifest=manifest)
