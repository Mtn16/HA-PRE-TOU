"""Tests for Czech public holiday calculations."""

from datetime import date
import unittest

import tests.mock_ha
from custom_components.pre_tou.parser import get_easter_sunday, is_czech_holiday


class TestCzechHolidays(unittest.TestCase):
    """Test Czech holiday detection."""

    def test_fixed_holidays(self) -> None:
        """Test fixed date holidays."""
        fixed = [
            date(2026, 1, 1),   # Nový rok
            date(2026, 5, 1),   # Svátek práce
            date(2026, 5, 8),   # Den vítězství
            date(2026, 7, 5),   # Cyril a Metoděj
            date(2026, 7, 6),   # Jan Hus
            date(2026, 9, 28),  # Den české státnosti
            date(2026, 10, 28), # Den vzniku ČSR
            date(2026, 11, 17), # Den boje za svobodu a demokracii
            date(2026, 12, 24), # Štědrý den
            date(2026, 12, 25), # 1. svátek vánoční
            date(2026, 12, 26), # 2. svátek vánoční
        ]
        for d in fixed:
            self.assertTrue(is_czech_holiday(d), f"{d} should be a holiday")

    def test_non_holidays(self) -> None:
        """Test regular non-holiday days."""
        regular = [
            date(2026, 1, 2),
            date(2026, 5, 2),
            date(2026, 10, 7),
            date(2026, 12, 23),
        ]
        for d in regular:
            self.assertFalse(is_czech_holiday(d), f"{d} should NOT be a holiday")

    def test_easter_holidays(self) -> None:
        """Test Good Friday and Easter Monday for several years."""
        # 2024: Easter March 31, Good Friday March 29, Easter Monday April 1
        self.assertEqual(get_easter_sunday(2024), date(2024, 3, 31))
        self.assertTrue(is_czech_holiday(date(2024, 3, 29)))
        self.assertTrue(is_czech_holiday(date(2024, 4, 1)))

        # 2025: Easter April 20, Good Friday April 18, Easter Monday April 21
        self.assertEqual(get_easter_sunday(2025), date(2025, 4, 20))
        self.assertTrue(is_czech_holiday(date(2025, 4, 18)))
        self.assertTrue(is_czech_holiday(date(2025, 4, 21)))

        # 2026: Easter April 5, Good Friday April 3, Easter Monday April 6
        self.assertEqual(get_easter_sunday(2026), date(2026, 4, 5))
        self.assertTrue(is_czech_holiday(date(2026, 4, 3)))
        self.assertTrue(is_czech_holiday(date(2026, 4, 6)))


if __name__ == "__main__":
    unittest.main()
