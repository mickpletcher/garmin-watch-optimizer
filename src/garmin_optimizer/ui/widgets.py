from __future__ import annotations

from PySide6.QtWidgets import QLabel


class StatusLabel(QLabel):
    def set_status(self, state: str, detail: str = "") -> None:
        text = f"{state}"
        if detail:
            text = f"{state}: {detail}"
        self.setText(text)
