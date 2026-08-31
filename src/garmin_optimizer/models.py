from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DESTRUCTIVE = "destructive"
    UNKNOWN = "unknown"


class AuthenticationState(StrEnum):
    AUTHENTICATED = "authenticated"
    SIGN_IN_REQUIRED = "sign_in_required"
    UNKNOWN = "unknown"


class CapabilitySupport(StrEnum):
    OBSERVED = "observed"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class SimulationOutcome(StrEnum):
    RUNNING = "running"
    RESTORED = "restored"
    FAILED_RESTORED = "failed_restored"
    AMBIGUOUS_RESTORED = "ambiguous_restored"
    RESTORE_FAILED = "restore_failed"


class AndroidDevice(BaseModel):
    serial: str
    state: str
    manufacturer: str | None = None
    model: str | None = None
    android_version: str | None = None


class GarminApp(BaseModel):
    package_name: str
    activity_name: str | None = None
    app_version: str | None = None
    confidence: float = 0.0


class GarminDevice(BaseModel):
    display_name: str
    model_hint: str | None = None
    firmware_version: str | None = None
    connected_state: str | None = None
    identity_source: str = "garmin_connect_ui"


class DiscoveredSetting(BaseModel):
    id: str
    screen_path: list[str]
    label: str
    current_value: str | None
    selectable_values: list[str] = Field(default_factory=list)
    resource_id: str | None = None
    content_description: str | None = None
    confidence: float
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    writable_candidate: bool = False
    notes: str = ""


class Capability(BaseModel):
    id: str
    title: str
    support: CapabilitySupport
    access: str = "read_only"
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    evidence: list[str] = Field(default_factory=list)


class CapabilityManifest(BaseModel):
    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    transport: str = "android_ui_research"
    research_only: bool = True
    app_package: str
    app_version: str | None = None
    device_model: str | None = None
    firmware_version: str | None = None
    capabilities: list[Capability] = Field(default_factory=list)


class JournalEvent(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event: str
    status: str
    detail: str = ""


class WriteSimulationTransaction(BaseModel):
    transaction_id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    setting_id: str
    label: str
    risk_level: RiskLevel
    original_value: str
    temporary_value: str
    user_confirmed: bool
    outcome: SimulationOutcome = SimulationOutcome.RUNNING
    change_verified: bool = False
    ambiguous_write: bool = False
    restore_attempted: bool = False
    restore_verified: bool = False
    errors: list[str] = Field(default_factory=list)
    events: list[JournalEvent] = Field(default_factory=list)


class SnapshotArtifact(BaseModel):
    schema_version: str = "1.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    host_os: str
    python_version: str
    adb_version: str | None = None
    appium_status: str | None = None
    authentication_state: AuthenticationState = AuthenticationState.UNKNOWN
    device: AndroidDevice | None = None
    garmin_app: GarminApp | None = None
    garmin_device: GarminDevice | None = None
    capability_manifest: CapabilityManifest | None = None
    screens_reached: list[str] = Field(default_factory=list)
    settings: list[DiscoveredSetting] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PocStatus(BaseModel):
    level: int
    summary: str
    warnings: list[str] = Field(default_factory=list)
