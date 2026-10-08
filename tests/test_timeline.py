"""Tests for PRE TOU timeline and state calculations."""

from datetime import datetime, timezone
import os
import unittest
import zoneinfo

import tests.mock_ha
from custom_components.pre_tou.parser import PreTouDatabase, calculate_schedule_state


class TestPreTouTimeline(unittest.TestCase):
    """Test timeline transitions and state calculations."""

    def setUp(self) -> None:
        """Set up test database."""
        self.csv_path = os.path.join(
            os.path.dirname(__file__), "..", "custom_components", "pre_tou", "data", "pre_tou_data.csv"
        )
        self.db = PreTouDatabase.from_csv_file(self.csv_path)
        self.tz = zoneinfo.ZoneInfo("Europe/Prague")

    def test_td25_001_state_transitions(self) -> None:
        """Test TD25_001 (NT at 01:00-06:00 and 13:00-16:00 on weekdays)."""
        item = self.db.get("TD25_001")
        self.assertIsNotNone(item)

        # Wednesday 2026-10-07 00:30 (before first NT)
        t_0030 = datetime(2026, 10, 7, 0, 30, tzinfo=self.tz)
        res = calculate_schedule_state(item.tariff_schedule, t_0030)
        self.assertFalse(res["is_active"]) # VT active
        self.assertEqual(res["next_start"], datetime(2026, 10, 7, 1, 0, tzinfo=self.tz)) # next NT
        self.assertEqual(res["next_end"], datetime(2026, 10, 7, 6, 0, tzinfo=self.tz)) # next VT

        # Wednesday 2026-10-07 03:00 (during first NT)
        t_0300 = datetime(2026, 10, 7, 3, 0, tzinfo=self.tz)
        res = calculate_schedule_state(item.tariff_schedule, t_0300)
        self.assertTrue(res["is_active"]) # NT active
        self.assertEqual(res["next_start"], datetime(2026, 10, 7, 13, 0, tzinfo=self.tz)) # next NT
        self.assertEqual(res["next_end"], datetime(2026, 10, 7, 6, 0, tzinfo=self.tz)) # next VT

        # Wednesday 2026-10-07 14:00 (during second NT)
        t_1400 = datetime(2026, 10, 7, 14, 0, tzinfo=self.tz)
        res = calculate_schedule_state(item.tariff_schedule, t_1400)
        self.assertTrue(res["is_active"]) # NT active
        self.assertEqual(res["next_start"], datetime(2026, 10, 8, 1, 0, tzinfo=self.tz)) # next NT tomorrow
        self.assertEqual(res["next_end"], datetime(2026, 10, 7, 16, 0, tzinfo=self.tz)) # next VT today 16:00

    def test_td61_weekend_behavior(self) -> None:
        """Test TD61_001 weekend schedule (Fri 12:00 to Sun 22:00)."""
        item = self.db.get("TD61_001")
        self.assertIsNotNone(item)

        # Wednesday 2026-10-07 12:00 -> VT active, next NT on Friday 12:00
        t_wed = datetime(2026, 10, 7, 12, 0, tzinfo=self.tz)
        res = calculate_schedule_state(item.tariff_schedule, t_wed)
        self.assertFalse(res["is_active"])
        self.assertEqual(res["next_start"], datetime(2026, 10, 9, 12, 0, tzinfo=self.tz))

        # Friday 2026-10-09 14:00 -> NT active, next VT on Sunday 22:00
        t_fri = datetime(2026, 10, 9, 14, 0, tzinfo=self.tz)
        res = calculate_schedule_state(item.tariff_schedule, t_fri)
        self.assertTrue(res["is_active"])
        self.assertEqual(res["next_end"], datetime(2026, 10, 11, 22, 0, tzinfo=self.tz))

        # Saturday 2026-10-10 12:00 -> NT active continuously
        t_sat = datetime(2026, 10, 10, 12, 0, tzinfo=self.tz)
        res = calculate_schedule_state(item.tariff_schedule, t_sat)
        self.assertTrue(res["is_active"])
        self.assertEqual(res["next_end"], datetime(2026, 10, 11, 22, 0, tzinfo=self.tz))

        # Sunday 2026-10-11 23:00 -> VT active (after 22:00)
        t_sun = datetime(2026, 10, 11, 23, 0, tzinfo=self.tz)
        res = calculate_schedule_state(item.tariff_schedule, t_sun)
        self.assertFalse(res["is_active"])
        self.assertEqual(res["next_start"], datetime(2026, 10, 16, 12, 0, tzinfo=self.tz))


if __name__ == "__main__":
    unittest.main()
