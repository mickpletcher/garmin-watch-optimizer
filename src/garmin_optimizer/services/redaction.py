from __future__ import annotations

import re
import xml.etree.ElementTree as et
from collections.abc import Mapping, Sequence
from typing import Any


class RedactionService:
    REDACTED = "<redacted>"
    SAFE_HASH_KEYS = {"sha256"}
    SAFE_GENERATED_ID_KEYS = {"job_id", "operation_id", "transaction_id"}
    SAFE_SEMANTIC_ID_KEYS = {"id", "setting_id"}
    SENSITIVE_KEYS = {
        "authorization",
        "cookie",
        "display_name",
        "email",
        "password",
        "phone",
        "secret",
        "serial",
        "ssid",
        "token",
        "unit_id",
        "username",
        "wifi_password",
    }
    SAFE_UI_TEXT = {
        "auto",
        "battery saver",
        "connected",
        "device settings",
        "devices",
        "enduro 2",
        "english",
        "firmware version",
        "garmin devices",
        "home",
        "language",
        "metric",
        "more",
        "software version",
        "statute",
        "syncing",
        "system",
        "today",
        "units",
    }
    SENSITIVE_LABEL_TERMS = {
        "account",
        "contact",
        "email",
        "emergency",
        "location",
        "network",
        "payment",
        "phone",
        "safety",
        "ssid",
        "wallet",
        "wi-fi",
        "wifi",
    }
    PATTERNS = (
        (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+"), "<redacted-email>"),
        (re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<redacted-device-id>"),
        (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b"), "<redacted-id>"),
        (re.compile(r"\b(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*[0-9])[A-Za-z0-9]{16,}\b"), "<redacted-id>"),
        (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer <redacted-token>"),
        (re.compile(r"(?i)\b(?:password|token|secret|authorization|cookie)\s*[:=]\s*[^\s,;]+"), "<redacted-secret>"),
        (re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)"), "<redacted-phone>"),
    )

    def redact_text(self, value: str) -> str:
        redacted = value
        for pattern, replacement in self.PATTERNS:
            redacted = pattern.sub(replacement, redacted)
        return redacted

    def redact_setting_value(self, label: str, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = label.casefold()
        if any(term in lowered for term in self.SENSITIVE_LABEL_TERMS):
            return "<redacted-sensitive-value>"
        return self.redact_text(value)

    def redact_xml(self, raw: str) -> str:
        try:
            root = et.fromstring(raw)
        except et.ParseError:
            return self.redact_text(raw)
        for node in root.iter():
            for attribute in ("text", "content-desc"):
                value = (node.attrib.get(attribute) or "").strip()
                if not value:
                    continue
                sanitized = self.redact_text(value)
                if sanitized.casefold() not in self.SAFE_UI_TEXT:
                    sanitized = "<redacted-ui-text>"
                node.set(attribute, sanitized)
        return et.tostring(root, encoding="unicode")

    def redact_data(self, value: Any, key: str | None = None) -> Any:
        if key and key.casefold() in self.SENSITIVE_KEYS:
            return self.REDACTED
        if (
            key
            and key.casefold() in self.SAFE_HASH_KEYS
            and isinstance(value, str)
            and re.fullmatch(r"[0-9a-f]{64}", value)
        ):
            return value
        if (
            key
            and key.casefold() in self.SAFE_GENERATED_ID_KEYS
            and isinstance(value, str)
            and re.fullmatch(r"[0-9a-f]{32}", value)
        ):
            return value
        if (
            key
            and key.casefold() in self.SAFE_SEMANTIC_ID_KEYS
            and isinstance(value, str)
            and re.fullmatch(r"[a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+)+", value)
        ):
            return value
        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, Mapping):
            redacted = {
                str(item_key): self.redact_data(item_value, str(item_key))
                for item_key, item_value in value.items()
            }
            if "label" in redacted and "current_value" in redacted:
                redacted["current_value"] = self.redact_setting_value(
                    str(redacted["label"]),
                    str(redacted["current_value"]) if redacted["current_value"] is not None else None,
                )
            return redacted
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [self.redact_data(item) for item in value]
        return value
