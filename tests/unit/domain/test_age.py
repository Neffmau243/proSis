from datetime import date

import pytest

from app.domain.age import calendar_age, completed_months


def test_completed_months_uses_calendar_not_days() -> None:
    assert completed_months(date(2024, 1, 31), date(2024, 2, 29)) == 0
    assert completed_months(date(2024, 1, 31), date(2024, 3, 31)) == 2


def test_calendar_age_preserves_calendar_components() -> None:
    age = calendar_age(date(2003, 4, 3), date(2026, 2, 9))

    assert (age.years, age.months, age.days) == (22, 10, 6)
    assert age.display == "22 años, 10 meses y 6 días"


def test_calendar_age_handles_leap_day_with_last_valid_day_policy() -> None:
    age = calendar_age(date(2024, 2, 29), date(2025, 2, 28))

    assert (age.years, age.months, age.days) == (1, 0, 0)


def test_age_rejects_reference_before_birth() -> None:
    with pytest.raises(ValueError):
        completed_months(date(2025, 1, 1), date(2024, 12, 31))
