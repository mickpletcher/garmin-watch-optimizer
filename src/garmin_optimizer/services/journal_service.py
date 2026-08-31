from __future__ import annotations

from pathlib import Path

from garmin_optimizer.exceptions import JournalWriteError
from garmin_optimizer.models import JournalEvent, WriteSimulationTransaction
from garmin_optimizer.services.persistence import atomic_write_json
from garmin_optimizer.services.redaction import RedactionService


class TransactionJournalService:
    def __init__(self, journals_dir: Path, redactor: RedactionService) -> None:
        self.journals_dir = journals_dir
        self.redactor = redactor

    def path_for(self, transaction: WriteSimulationTransaction) -> Path:
        return self.journals_dir / f"simulation_{transaction.transaction_id}.json"

    def record(
        self,
        transaction: WriteSimulationTransaction,
        event: str,
        status: str,
        detail: str = "",
    ) -> Path:
        transaction.events.append(
            JournalEvent(
                event=event,
                status=status,
                detail=self.redactor.redact_text(detail),
            )
        )
        path = self.path_for(transaction)
        try:
            payload = self.redactor.redact_data(transaction.model_dump(mode="json"))
            atomic_write_json(path, payload)
        except OSError as exc:
            raise JournalWriteError(f"Unable to persist simulation journal: {exc}") from exc
        return path
