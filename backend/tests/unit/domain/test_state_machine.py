import pytest

from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.exceptions import ActionNotAllowedError, IllegalTransitionError
from domain.tickets.state_machine import ensure_transition, next_statuses

S = TicketStatus


def test_dispatcher_moves_ticket_through_work():
    for current, target in [
        (S.REGISTERED, S.ACKNOWLEDGED),
        (S.ACKNOWLEDGED, S.IN_PROGRESS),
        (S.IN_PROGRESS, S.DONE),
    ]:
        ensure_transition(current, target, ActorRole.DISPATCHER)


def test_only_resident_confirms_or_reopens():
    ensure_transition(S.DONE, S.CONFIRMED, ActorRole.RESIDENT)
    ensure_transition(S.DONE, S.IN_PROGRESS, ActorRole.RESIDENT)
    with pytest.raises(ActionNotAllowedError):
        ensure_transition(S.DONE, S.CONFIRMED, ActorRole.DISPATCHER)


def test_resident_cannot_close_own_ticket_as_done():
    with pytest.raises(ActionNotAllowedError):
        ensure_transition(S.IN_PROGRESS, S.DONE, ActorRole.RESIDENT)


@pytest.mark.parametrize("terminal", [S.CONFIRMED, S.REJECTED])
def test_terminal_statuses_have_no_exits(terminal):
    for role in ActorRole:
        assert next_statuses(terminal, role) == []
    with pytest.raises(IllegalTransitionError):
        ensure_transition(terminal, S.IN_PROGRESS, ActorRole.DISPATCHER)


def test_next_statuses_drive_dispatcher_buttons():
    assert next_statuses(S.REGISTERED, ActorRole.DISPATCHER) == [
        S.ACKNOWLEDGED,
        S.IN_PROGRESS,
        S.DONE,
        S.REJECTED,
    ]
