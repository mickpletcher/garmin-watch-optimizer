from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as et
from pathlib import Path

from garmin_optimizer.exceptions import NavigationMismatchError
from garmin_optimizer.models import AuthenticationState, DiscoveredSetting, RiskLevel
from garmin_optimizer.services.persistence import atomic_write_text, utc_file_stamp
from garmin_optimizer.services.redaction import RedactionService


class UiDiscoveryService:
    def __init__(
        self,
        diagnostics_dir: Path,
        redactor: RedactionService,
        diagnostics_enabled: bool = False,
    ) -> None:
        self.diagnostics_dir = diagnostics_dir
        self.redactor = redactor
        self.diagnostics_enabled = diagnostics_enabled

    def _root(self, page_source: str) -> et.Element:
        try:
            return et.fromstring(page_source)
        except et.ParseError as exc:
            raise NavigationMismatchError("Garmin Connect returned malformed UI hierarchy XML.") from exc

    def visible_texts(self, page_source: str) -> list[str]:
        values: list[str] = []
        for node in self._root(page_source).iter():
            for attribute in ("text", "content-desc"):
                value = (node.attrib.get(attribute) or "").strip()
                if value and value not in values:
                    values.append(self.redactor.redact_text(value))
        return values

    def detect_authentication_state(self, page_source: str) -> AuthenticationState:
        texts = {value.casefold() for value in self.visible_texts(page_source)}
        sign_in_markers = {"sign in", "create account", "forgot password", "get started"}
        authenticated_markers = {"more", "garmin devices", "home", "today", "my day"}
        if texts & sign_in_markers:
            return AuthenticationState.SIGN_IN_REQUIRED
        if texts & authenticated_markers:
            return AuthenticationState.AUTHENTICATED
        return AuthenticationState.UNKNOWN

    def parse_page_source(self, page_source: str, screen_path: list[str]) -> list[DiscoveredSetting]:
        settings: list[DiscoveredSetting] = []
        for node in self._root(page_source).iter():
            resource_id = node.attrib.get("resource-id") or ""
            clickable = node.attrib.get("clickable", "false") == "true"
            if not clickable and "setting" not in resource_id.casefold():
                continue

            texts = self._node_texts(node)
            if len(texts) < 2:
                continue
            label = self.redactor.redact_text(texts[0])
            current_value = self.redactor.redact_setting_value(label, texts[1])
            if self._looks_like_noise(label) or current_value is None:
                continue

            confidence = 0.7
            if resource_id:
                confidence += 0.15
            if clickable:
                confidence += 0.1
            risk_level = self.classify_risk(label)
            settings.append(
                DiscoveredSetting(
                    id=self._make_id(screen_path, resource_id or label),
                    screen_path=[self.redactor.redact_text(part) for part in screen_path],
                    label=label,
                    current_value=current_value,
                    resource_id=resource_id or None,
                    content_description=self.redactor.redact_text(node.attrib.get("content-desc") or "") or None,
                    confidence=min(confidence, 0.99),
                    risk_level=risk_level,
                    writable_candidate=False,
                    notes="Read-only observation. No write capability is enabled.",
                )
            )

        deduped: dict[str, DiscoveredSetting] = {}
        for item in settings:
            existing = deduped.get(item.id)
            if existing is None or item.confidence > existing.confidence:
                deduped[item.id] = item
        return list(deduped.values())

    def dump_sanitized_xml(self, page_source: str, label: str, force: bool = False) -> Path | None:
        if not self.diagnostics_enabled and not force:
            return None
        safe_label = re.sub(r"[^a-zA-Z0-9_.-]+", "_", label).strip("_") or "dump"
        path = self.diagnostics_dir / f"{utc_file_stamp()}_{safe_label}.xml"
        atomic_write_text(path, self.redactor.redact_xml(page_source))
        return path

    def _node_texts(self, node: et.Element) -> list[str]:
        values: list[str] = []
        for child in node.iter():
            for attribute in ("text", "content-desc"):
                value = (child.attrib.get(attribute) or "").strip()
                if value and value not in values and not self._looks_like_noise(value):
                    values.append(value)
        return values

    def _make_id(self, screen_path: list[str], stable_value: str) -> str:
        raw = "/".join(screen_path + [stable_value.strip().casefold()])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    def _looks_like_noise(self, value: str) -> bool:
        if len(value) <= 1 or value.isdigit():
            return True
        return re.fullmatch(r"[0-9:/.]+", value) is not None

    def classify_risk(self, label: str) -> RiskLevel:
        lowered = label.casefold()
        destructive_terms = ["factory reset", "delete", "erase", "history"]
        high_terms = ["emergency", "payment", "wallet", "sensor", "wifi", "firmware", "safety", "pair"]
        medium_terms = ["gps", "battery", "power mode", "data screen", "control", "glance"]
        low_terms = ["units", "time format", "theme", "language", "favorite", "activity order"]
        if any(term in lowered for term in destructive_terms):
            return RiskLevel.DESTRUCTIVE
        if any(term in lowered for term in high_terms):
            return RiskLevel.HIGH
        if any(term in lowered for term in medium_terms):
            return RiskLevel.MEDIUM
        if any(term in lowered for term in low_terms):
            return RiskLevel.LOW
        return RiskLevel.HIGH
