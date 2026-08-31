from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from yaml.tokens import AliasToken, AnchorToken, TagToken

from garmin_optimizer.exceptions import ConfigurationError, ConfigurationSecurityError
from garmin_optimizer.models import (
    ConfigurationOverlay,
    DesiredConfiguration,
    OverlayConflict,
    OverlayResolution,
)
from garmin_optimizer.services.persistence import atomic_write_text
from garmin_optimizer.services.redaction import RedactionService


class ConfigurationService:
    MAX_CONFIG_BYTES = 1_048_576
    ALLOWED_SUFFIXES = {".json", ".yaml", ".yml"}

    def __init__(self, redactor: RedactionService) -> None:
        self.redactor = redactor

    def load(self, path: Path) -> DesiredConfiguration:
        text = self._read_text(path)
        return self.load_text(text, path.suffix)

    def load_overlay(self, path: Path) -> ConfigurationOverlay:
        text = self._read_text(path)
        payload = self._parse(text, path.suffix)
        self._reject_sensitive_data(payload)
        try:
            overlay = ConfigurationOverlay.model_validate(payload)
            DesiredConfiguration.validate_setting_ids(overlay.settings)
            return overlay
        except (ValidationError, ValueError) as exc:
            raise ConfigurationError(f"Invalid configuration overlay: {exc}") from exc

    def load_text(self, text: str, suffix: str = ".yaml") -> DesiredConfiguration:
        if len(text.encode("utf-8")) > self.MAX_CONFIG_BYTES:
            raise ConfigurationSecurityError("Configuration exceeds the 1 MiB safety limit.")
        payload = self._parse(text, suffix)
        self._reject_sensitive_data(payload)
        try:
            return DesiredConfiguration.model_validate(payload)
        except ValidationError as exc:
            raise ConfigurationError(f"Invalid desired configuration: {exc}") from exc

    def save(self, configuration: DesiredConfiguration, path: Path) -> Path:
        sanitized = self.redactor.redact_data(configuration.model_dump(mode="json"))
        content = yaml.safe_dump(sanitized, sort_keys=False, allow_unicode=True)
        atomic_write_text(path, content)
        return path

    def dump_text(self, configuration: DesiredConfiguration) -> str:
        sanitized = self.redactor.redact_data(configuration.model_dump(mode="json"))
        return str(yaml.safe_dump(sanitized, sort_keys=False, allow_unicode=True))

    def resolve_overlays(
        self,
        base: DesiredConfiguration,
        overlays: list[ConfigurationOverlay],
    ) -> OverlayResolution:
        payload = deepcopy(base.model_dump(mode="python"))
        settings = dict(payload["settings"])
        owners: dict[str, str] = {}
        conflicts: list[OverlayConflict] = []

        for overlay in overlays:
            DesiredConfiguration.validate_setting_ids(overlay.settings)
            for setting_id in sorted(overlay.settings):
                value = deepcopy(overlay.settings[setting_id])
                previous_owner = owners.get(setting_id)
                if previous_owner and settings.get(setting_id) != value:
                    conflicts.append(
                        OverlayConflict(
                            setting_id=setting_id,
                            previous_overlay=previous_owner,
                            replacing_overlay=overlay.name,
                        )
                    )
                settings[setting_id] = value
                owners[setting_id] = overlay.name

        payload["settings"] = {key: settings[key] for key in sorted(settings)}
        resolved = DesiredConfiguration.model_validate(payload)
        return OverlayResolution(
            configuration=resolved,
            applied_overlays=[overlay.name for overlay in overlays],
            conflicts=conflicts,
        )

    def _read_text(self, path: Path) -> str:
        if path.suffix.casefold() not in self.ALLOWED_SUFFIXES:
            raise ConfigurationError("Configuration must use .yaml, .yml, or .json.")
        if path.is_symlink():
            raise ConfigurationSecurityError("Symbolic-link configuration files are blocked.")
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise ConfigurationError(f"Unable to inspect configuration: {exc}") from exc
        if size > self.MAX_CONFIG_BYTES:
            raise ConfigurationSecurityError("Configuration exceeds the 1 MiB safety limit.")
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ConfigurationError(f"Unable to read configuration: {exc}") from exc

    def _parse(self, text: str, suffix: str) -> dict[str, Any]:
        try:
            if suffix.casefold() == ".json":
                payload = json.loads(text)
            else:
                for token in yaml.scan(text):
                    if isinstance(token, (AliasToken, AnchorToken, TagToken)):
                        raise ConfigurationSecurityError(
                            "YAML aliases, anchors, and explicit tags are blocked."
                        )
                payload = yaml.safe_load(text)
        except ConfigurationSecurityError:
            raise
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Configuration parsing failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise ConfigurationError("Configuration root must be an object.")
        return payload

    def _reject_sensitive_data(self, value: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                segments = {part for part in re.split(r"[._-]+", key_text.casefold()) if part}
                if segments & self.redactor.SENSITIVE_KEYS:
                    joined = ".".join(path + (key_text,))
                    raise ConfigurationSecurityError(f"Sensitive configuration key is prohibited: {joined}")
                self._reject_sensitive_data(item, path + (key_text,))
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                self._reject_sensitive_data(item, path + (str(index),))
            return
        if isinstance(value, str) and self.redactor.redact_text(value) != value:
            joined = ".".join(path) or "root"
            raise ConfigurationSecurityError(f"Sensitive value pattern is prohibited at: {joined}")
