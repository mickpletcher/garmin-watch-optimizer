from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from garmin_optimizer.exceptions import (
    AmbiguousWriteError,
    JournalWriteError,
    RestoreVerificationError,
    UnsafeWriteError,
    WriteVerificationError,
)
from garmin_optimizer.models import (
    DiscoveredSetting,
    RiskLevel,
    SimulationOutcome,
    WriteSimulationTransaction,
)
from garmin_optimizer.services.journal_service import TransactionJournalService


@dataclass
class SimulationHooks:
    read_current: Callable[[DiscoveredSetting], str]
    list_values: Callable[[DiscoveredSetting], list[str]]
    set_value: Callable[[DiscoveredSetting, str], None]


class WriteSimulationService:
    def validate_candidate(self, setting: DiscoveredSetting) -> None:
        if setting.risk_level is not RiskLevel.LOW:
            raise UnsafeWriteError(
                "Simulation permits only explicitly low risk settings. "
                f"'{setting.label}' is {setting.risk_level.value}."
            )
        if not setting.writable_candidate:
            raise UnsafeWriteError(f"Setting '{setting.label}' is not an approved simulation candidate.")
        if not setting.current_value:
            raise UnsafeWriteError(f"Setting '{setting.label}' has no known current value.")

    def execute(
        self,
        setting: DiscoveredSetting,
        temporary_value: str,
        user_confirmed: bool,
        hooks: SimulationHooks,
        journal: TransactionJournalService,
    ) -> WriteSimulationTransaction:
        self.validate_candidate(setting)
        if not user_confirmed:
            raise UnsafeWriteError("Simulation confirmation was not provided.")

        original = hooks.read_current(setting)
        if not original or original != setting.current_value:
            raise UnsafeWriteError("Simulation source value is missing or stale.")
        values = hooks.list_values(setting)
        if temporary_value == original or temporary_value not in values:
            raise UnsafeWriteError("Temporary value must be a different value from the supplied simulation choices.")

        transaction = WriteSimulationTransaction(
            setting_id=setting.id,
            label=setting.label,
            risk_level=setting.risk_level,
            original_value=original,
            temporary_value=temporary_value,
            user_confirmed=True,
        )
        journal.record(transaction, "preflight", "passed", "Simulation only. No device transport is available.")
        journal.record(transaction, "change_attempt", "started", f"Temporary value: {temporary_value}")

        try:
            hooks.set_value(setting, temporary_value)
            changed = hooks.read_current(setting)
        except Exception as exc:
            transaction.ambiguous_write = True
            transaction.errors.append(f"Ambiguous simulated change failure: {exc}")
            self._record_best_effort(journal, transaction, "change_attempt", "ambiguous", str(exc))
            restored = self._restore(setting, original, hooks, journal, transaction)
            transaction.outcome = (
                SimulationOutcome.AMBIGUOUS_RESTORED if restored else SimulationOutcome.RESTORE_FAILED
            )
            self._record_best_effort(journal, transaction, "transaction", transaction.outcome.value)
            if not restored:
                raise RestoreVerificationError("Ambiguous simulation failure was not restored.") from exc
            raise AmbiguousWriteError(
                "Simulation change outcome was ambiguous and the original value was restored."
            ) from exc

        if changed != temporary_value:
            transaction.errors.append("Post-change verification failed.")
            self._record_best_effort(journal, transaction, "change_verification", "failed")
            restored = self._restore(setting, original, hooks, journal, transaction)
            transaction.outcome = SimulationOutcome.FAILED_RESTORED if restored else SimulationOutcome.RESTORE_FAILED
            self._record_best_effort(journal, transaction, "transaction", transaction.outcome.value)
            if not restored:
                raise RestoreVerificationError(
                    "Simulation verification failed and the original value was not restored."
                )
            raise WriteVerificationError("Temporary simulation value could not be verified. Original value restored.")

        transaction.change_verified = True
        self._record_best_effort(journal, transaction, "change_verification", "passed")
        restored = self._restore(setting, original, hooks, journal, transaction)
        if not restored:
            transaction.outcome = SimulationOutcome.RESTORE_FAILED
            self._record_best_effort(journal, transaction, "transaction", transaction.outcome.value)
            raise RestoreVerificationError("Simulation restoration was attempted but not verified.")

        transaction.outcome = SimulationOutcome.RESTORED
        journal.record(transaction, "transaction", "restored")
        return transaction

    def _restore(
        self,
        setting: DiscoveredSetting,
        original: str,
        hooks: SimulationHooks,
        journal: TransactionJournalService,
        transaction: WriteSimulationTransaction,
    ) -> bool:
        transaction.restore_attempted = True
        self._record_best_effort(journal, transaction, "restore_attempt", "started")
        try:
            hooks.set_value(setting, original)
            transaction.restore_verified = hooks.read_current(setting) == original
        except Exception as exc:
            transaction.errors.append(f"Restoration failure: {exc}")
            transaction.restore_verified = False
        self._record_best_effort(
            journal,
            transaction,
            "restore_verification",
            "passed" if transaction.restore_verified else "failed",
        )
        return transaction.restore_verified

    def _record_best_effort(
        self,
        journal: TransactionJournalService,
        transaction: WriteSimulationTransaction,
        event: str,
        status: str,
        detail: str = "",
    ) -> None:
        try:
            journal.record(transaction, event, status, detail)
        except JournalWriteError as exc:
            transaction.errors.append(str(exc))
