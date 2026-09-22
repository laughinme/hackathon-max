from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from domain.tickets.calendar import add_working_days
from domain.tickets.sla import EMERGENCY_RULE, FALLBACK_RULE, ROUTINE_RULES, SlaPolicy

CREATED = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)  # Wednesday, 12:00 MSK
MSK = ZoneInfo("Europe/Moscow")


def test_emergency_overrides_category_and_sets_reaction_deadline():
    deadlines = SlaPolicy().deadlines("lift", True, CREATED)
    assert deadlines.react_by == CREATED + timedelta(minutes=30)
    assert deadlines.resolve_by == CREATED + timedelta(days=3)
    assert deadlines.legal_basis == EMERGENCY_RULE.legal_basis


@pytest.mark.parametrize(
    ("category", "days"),
    [("lift", 1), ("water", 1), ("heating", 1), ("door", 1), ("light", 7)],
)
def test_routine_categories_use_their_own_rule(category, days):
    deadlines = SlaPolicy().deadlines(category, False, CREATED)
    assert deadlines.resolve_by == CREATED + timedelta(days=days)
    assert deadlines.react_by is None


def test_unknown_category_falls_back_to_ten_working_days():
    deadlines = SlaPolicy().deadlines("other", False, CREATED)
    assert deadlines.legal_basis == FALLBACK_RULE.legal_basis
    # 23.09 (Wed) + 10 working days = 07.10 (Wed), end of day in Moscow time.
    assert deadlines.resolve_by.astimezone(MSK).date() == datetime(2026, 10, 7).date()


def test_every_rule_names_its_legal_basis():
    for rule in (EMERGENCY_RULE, FALLBACK_RULE, *ROUTINE_RULES.values()):
        assert rule.legal_basis


def test_working_days_skip_weekends_and_holidays():
    friday = datetime(2026, 10, 30, 10, 0, tzinfo=MSK)
    # Mon 02.11, Tue 03.11; Wed 04.11 is a holiday; Thu 05.11.
    assert add_working_days(friday, 3).date() == datetime(2026, 11, 5).date()
