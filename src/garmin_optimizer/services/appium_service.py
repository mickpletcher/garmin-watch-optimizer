from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from urllib import error, request
from urllib.parse import urlparse

from garmin_optimizer.exceptions import AppiumUnavailableError, UiAutomator2UnavailableError

if TYPE_CHECKING:
    from appium.webdriver.webdriver import WebDriver
else:
    WebDriver = Any

webdriver: Any
UiAutomator2Options: Any

try:
    from appium import webdriver as _webdriver
    from appium.options.android import UiAutomator2Options as _UiAutomator2Options

    webdriver = _webdriver
    UiAutomator2Options = _UiAutomator2Options
except Exception:  # pragma: no cover
    webdriver = None
    UiAutomator2Options = None


class AppiumService:
    LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}

    def __init__(self, appium_url: str) -> None:
        self.appium_url = appium_url.rstrip("/")
        hostname = urlparse(self.appium_url).hostname
        if hostname not in self.LOCAL_HOSTS:
            raise AppiumUnavailableError("Appium must use a loopback address. Remote Appium endpoints are blocked.")
        self.driver: WebDriver | None = None

    def check_endpoint(self, timeout_seconds: int = 5) -> dict[str, Any]:
        url = f"{self.appium_url}/status"
        req = request.Request(url, method="GET")
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except (error.URLError, json.JSONDecodeError) as exc:
            raise AppiumUnavailableError(
                f"Appium endpoint {url} is not ready. Start the local Appium server. Details: {exc}"
            ) from exc

        value = payload.get("value", payload) if isinstance(payload, dict) else {}
        ready = bool(value.get("ready")) if isinstance(value, dict) else False
        return {"ready": response.status == 200 and ready, "endpoint": self.appium_url}

    def create_session(
        self,
        serial: str,
        package_name: str,
        activity_name: str | None = None,
    ) -> WebDriver:
        if webdriver is None or UiAutomator2Options is None:
            raise UiAutomator2UnavailableError(
                "Appium Python client is unavailable. Install dependencies with pip install -e '.[dev]'."
            )

        options = UiAutomator2Options()
        options.set_capability("platformName", "Android")
        options.set_capability("appium:automationName", "UiAutomator2")
        options.set_capability("appium:udid", serial)
        options.set_capability("appium:noReset", True)
        options.set_capability("appium:fullReset", False)
        options.set_capability("appium:newCommandTimeout", 120)
        options.set_capability("appium:autoGrantPermissions", False)
        options.set_capability("appium:appPackage", package_name)
        if activity_name:
            options.set_capability("appium:appActivity", activity_name)

        try:
            self.driver = webdriver.Remote(self.appium_url, options=options)
        except Exception as exc:  # pragma: no cover
            raise UiAutomator2UnavailableError(
                f"Failed to create a read-only UiAutomator2 research session for device {serial}: {exc}"
            ) from exc
        return self.driver

    @contextmanager
    def session(
        self,
        serial: str,
        package_name: str,
        activity_name: str | None = None,
    ) -> Iterator[WebDriver]:
        driver = self.create_session(serial, package_name, activity_name)
        try:
            yield driver
        finally:
            self.close_session()

    def close_session(self) -> None:
        if self.driver is not None:
            try:
                self.driver.quit()
            finally:
                self.driver = None

    def activate_app(self, package_name: str) -> None:
        if not self.driver:
            raise UiAutomator2UnavailableError("Appium session is not connected.")
        self.driver.activate_app(package_name)

    def find_elements(self, by: str, value: str):
        if not self.driver:
            raise UiAutomator2UnavailableError("Appium session is not connected.")
        return self.driver.find_elements(by, value)

    def page_source(self) -> str:
        if not self.driver:
            raise UiAutomator2UnavailableError("Appium session is not connected.")
        return self.driver.page_source

    def back(self) -> None:
        if not self.driver:
            raise UiAutomator2UnavailableError("Appium session is not connected.")
        self.driver.back()
