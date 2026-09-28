from application.ports.ai import DialogTurn
from application.tickets.draft_complaint import DraftComplaint
from application.tickets.triage_complaint import TriageComplaint
from domain.tickets.sla import SlaPolicy
from infrastructure.ai.stub import StubAIService
from tests.fakes import FixedClock, StaticClassifier, classification


def draft_complaint(**overrides) -> DraftComplaint:
    triage = TriageComplaint(
        StaticClassifier(classification(**overrides)), SlaPolicy(), FixedClock(), 0.6
    )
    return DraftComplaint(StubAIService(), triage)


async def test_asks_a_question_until_there_are_details():
    step = await draft_complaint().execute(
        [DialogTurn("user", "Лифт не работает")], category_code=None
    )
    assert not step.is_ready
    assert step.question and step.triage is None


async def test_drafts_with_deadline_once_enough_is_said():
    turns = [
        DialogTurn("user", "Лифт не работает"),
        DialogTurn("bot", "Какой подъезд?"),
        DialogTurn("user", "Второй подъезд, застрял на 5 этаже"),
    ]
    step = await draft_complaint().execute(turns, category_code="lift")
    assert step.is_ready and step.draft
    assert step.triage is not None
    assert step.triage.category_code == "lift"
    assert not step.triage.needs_emergency_confirmation


async def test_unsure_emergency_needs_confirmation():
    turns = [DialogTurn("user", "Течёт"), DialogTurn("user", "В подвале, сильно")]
    step = await draft_complaint(emergency_confidence=0.3).execute(turns, None)
    assert step.triage is not None
    assert step.triage.needs_emergency_confirmation
    assert step.triage.is_emergency  # fail-safe until the resident answers
