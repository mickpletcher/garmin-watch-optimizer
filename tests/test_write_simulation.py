import json
from pathlib import Path

import pytest

from garmin_optimizer.exceptions import (
    AmbiguousWriteError,
    JournalWriteError,
    RestoreVerificationError,
    UnsafeWriteError,
    WriteVerificationError,
)
from garmin_optimizer.models import DiscoveredSetting, RiskLevel, SimulationOutcome
from garmin_optimizer.services.journal_service import TransactionJournalService
from garmin_optimizer.services.redaction import RedactionService
from garmin_optimizer.services.write_simulation import SimulationHooks, WriteSimulationService


def candidate(risk: RiskLevel = RiskLevel.LOW, writable: bool = True) -> DiscoveredSetting:
    return DiscoveredSetting(
        id="simulation.units",
        screen_path=["Simulation"],
        label="Units",
        current_value="Statute",
        selectable_values=["Statute", "Metric"],
        confidence=1.0,
        risk_level=risk,
        writable_candidate=writable,
    )


def hooks_for(state: dict[str, str], setter=None) -> SimulationHooks:
    return SimulationHooks(
        read_current=lambda _: state["value"],
        list_values=lambda _: ["Statute", "Metric"],
        set_value=setter or (lambda _, value: state.__setitem__("value", value)),
    )


@pytest.mark.parametrize(
    "risk",
    [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.DESTRUCTIVE, RiskLevel.UNKNOWN],
)
def test_every_non_low_risk_is_blocked(tmp_path: Path, risk: RiskLevel) -> None:
    state = {"value": "Statute"}
    with pytest.raises(UnsafeWriteError):
        WriteSimulationService().execute(
            candidate(risk), "Metric", True, hooks_for(state), TransactionJournalService(tmp_path, RedactionService())
        )
    assert state["value"] == "Statute"


def test_candidate_confirmation_staleness_and_choice_are_enforced(tmp_path: Path) -> None:
    journal = TransactionJournalService(tmp_path, RedactionService())
    service = WriteSimulationService()
    state = {"value": "Statute"}
    with pytest.raises(UnsafeWriteError):
        service.execute(candidate(writable=False), "Metric", True, hooks_for(state), journal)
    with pytest.raises(UnsafeWriteError):
        service.execute(candidate(), "Metric", False, hooks_for(state), journal)
    state["value"] = "Metric"
    with pytest.raises(UnsafeWriteError):
        service.execute(candidate(), "Metric", True, hooks_for(state), journal)
    state["value"] = "Statute"
    with pytest.raises(UnsafeWriteError):
        service.execute(candidate(), "Imperial", True, hooks_for(state), journal)


def test_successful_simulation_is_restored_and_journaled(tmp_path: Path) -> None:
    state = {"value": "Statute"}
    journal = TransactionJournalService(tmp_path, RedactionService())
    transaction = WriteSimulationService().execute(candidate(), "Metric", True, hooks_for(state), journal)

    assert transaction.outcome is SimulationOutcome.RESTORED
    assert transaction.change_verified and transaction.restore_verified
    assert state["value"] == "Statute"
    persisted = json.loads(journal.path_for(transaction).read_text(encoding="utf-8"))
    assert persisted["outcome"] == "restored"
    assert persisted["events"][0]["event"] == "preflight"


def test_ambiguous_failure_restores_and_is_persisted(tmp_path: Path) -> None:
    state = {"value": "Statute"}
    calls = 0

    def set_then_fail(_, value: str) -> None:
        nonlocal calls
        calls += 1
        state["value"] = value
        if calls == 1:
            raise RuntimeError("transport failed after mutation token=secret-value")

    journal = TransactionJournalService(tmp_path, RedactionService())
    with pytest.raises(AmbiguousWriteError):
        WriteSimulationService().execute(candidate(), "Metric", True, hooks_for(state, set_then_fail), journal)
    path = next(tmp_path.glob("simulation_*.json"))
    content = path.read_text(encoding="utf-8")
    assert state["value"] == "Statute"
    assert json.loads(content)["outcome"] == "ambiguous_restored"
    assert "secret-value" not in content


def test_verification_failure_restores(tmp_path: Path) -> None:
    state = {"value": "Statute"}
    calls = 0

    def ignore_first(_, value: str) -> None:
        nonlocal calls
        calls += 1
        if calls > 1:
            state["value"] = value

    with pytest.raises(WriteVerificationError):
        WriteSimulationService().execute(
            candidate(),
            "Metric",
            True,
            hooks_for(state, ignore_first),
            TransactionJournalService(tmp_path, RedactionService()),
        )
    assert state["value"] == "Statute"


def test_restore_failure_is_loud_and_persisted(tmp_path: Path) -> None:
    state = {"value": "Statute"}
    calls = 0

    def refuse_restore(_, value: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            state["value"] = value

    with pytest.raises(RestoreVerificationError):
        WriteSimulationService().execute(
            candidate(),
            "Metric",
            True,
            hooks_for(state, refuse_restore),
            TransactionJournalService(tmp_path, RedactionService()),
        )
    persisted = json.loads(next(tmp_path.glob("simulation_*.json")).read_text(encoding="utf-8"))
    assert state["value"] == "Metric"
    assert persisted["outcome"] == "restore_failed"


def test_journal_failure_blocks_before_simulated_mutation(tmp_path: Path) -> None:
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("file", encoding="utf-8")
    state = {"value": "Statute"}
    with pytest.raises(JournalWriteError):
        WriteSimulationService().execute(
            candidate(),
            "Metric",
            True,
            hooks_for(state),
            TransactionJournalService(blocked, RedactionService()),
        )
    assert state["value"] == "Statute"
