from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    appium_url: str = Field(default="http://127.0.0.1:4723")
    runtime_dir: Path = Field(default=Path("runtime"))
    diagnostics_enabled: bool = Field(default=False)
    android_ui_research_enabled: bool = Field(default=False)
    target_watch_model: str = Field(default="Enduro 2")

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            appium_url=os.getenv("GARMIN_OPT_APPIUM_URL", "http://127.0.0.1:4723"),
            runtime_dir=Path(os.getenv("GARMIN_OPT_RUNTIME_DIR", "runtime")),
            diagnostics_enabled=os.getenv("GARMIN_OPT_DIAGNOSTICS", "0") == "1",
            android_ui_research_enabled=os.getenv("GARMIN_OPT_ENABLE_ANDROID_UI_RESEARCH", "0") == "1",
            target_watch_model=os.getenv("GARMIN_OPT_TARGET_WATCH", "Enduro 2"),
        )

    @property
    def logs_dir(self) -> Path:
        return self.runtime_dir / "logs"

    @property
    def snapshots_dir(self) -> Path:
        return self.runtime_dir / "snapshots"

    @property
    def reports_dir(self) -> Path:
        return self.runtime_dir / "reports"

    @property
    def diagnostics_dir(self) -> Path:
        return self.runtime_dir / "diagnostics"

    @property
    def manifests_dir(self) -> Path:
        return self.runtime_dir / "manifests"

    @property
    def journals_dir(self) -> Path:
        return self.runtime_dir / "journals"
