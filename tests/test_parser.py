"""Tests for PRE TOU parser."""

import os
import unittest
from datetime import date, time

import tests.mock_ha
from custom_components.pre_tou.parser import (
    PreTouDatabase,
    parse_time_cell,
    time_str_to_seconds,
    seconds_to_time_str,
)


class TestPreTouParser(unittest.TestCase):
    """Test parser functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.csv_path = os.path.join(
            os.path.dirname(__file__), "..", "custom_components", "pre_tou", "data", "pre_tou_data.csv"
        )
        self.db = PreTouDatabase.from_csv_file(self.csv_path)

    def test_database_loads_all_overview_items(self) -> None:
        """Test that all 43 items from overview table are loaded."""
        self.assertGreaterEqual(len(self.db.items), 43)

        expected_ids = [
            "TC25_001", "TC25_002", "TC25_003", "TC25_004",
            "TC26_001", "TC26_002", "TC26_003", "TC26_004",
            "TC27_001", "TC35_001", "TC45_001", "TC45_002",
            "TC46_001", "TC55_001",
            "TD25_001", "TD25_002", "TD25_003", "TD25_004", "TD25_005",
            "TD25_006", "TD25_007", "TD25_008", "TD25_009",
            "TD26_001", "TD26_002", "TD26_003", "TD26_004", "TD26_005",
            "TD26_006", "TD26_007", "TD26_008", "TD26_009",
            "TD27_001", "TD35_001",
            "TD45_001", "TD45_002", "TD45_003", "TD45_004", "TD45_005",
            "TD55_001", "TD57_001", "TD57_002", "TD61_001"
        ]
        for tid in expected_ids:
            item = self.db.get(tid)
            self.assertIsNotNone(item, f"Expected {tid} to be in database")
            self.assertTrue(item.display_name.startswith(tid))

    def test_parse_excel_fractions(self) -> None:
        """Test parsing Excel decimal day fractions."""
        self.assertEqual(parse_time_cell("0.59375"), "14:15:00")
        self.assertEqual(parse_time_cell("0.70833333333333337"), "17:00:00")
        self.assertEqual(parse_time_cell("0.91666666666666663"), "22:00:00")
        self.assertEqual(parse_time_cell("0.94791666666666663"), "22:45:00")

    def test_parse_standard_time_strings(self) -> None:
        """Test parsing standard HH:MM:SS strings."""
        self.assertEqual(parse_time_cell("00:00:00"), "00:00:00")
        self.assertEqual(parse_time_cell("06:45:00"), "06:45:00")
        self.assertEqual(parse_time_cell("13:15"), "13:15:00")
        self.assertEqual(parse_time_cell(""), None)

    def test_seconds_conversion(self) -> None:
        """Test converting between seconds and HH:MM:SS."""
        self.assertEqual(time_str_to_seconds("01:00:00"), 3600)
        self.assertEqual(seconds_to_time_str(3600), "01:00:00")
        self.assertEqual(time_str_to_seconds("14:15:00"), 51300)
        self.assertEqual(seconds_to_time_str(51300), "14:15:00")

    def test_tariff_durations(self) -> None:
        """Test total hours of NT for specific tariffs."""
        def calc_hours(intervals):
            return sum((iv.end_sec - iv.start_sec) for iv in intervals) / 3600

        # D25d (TD25_001) should have 8 hours of NT
        td25 = self.db.get("TD25_001")
        self.assertIsNotNone(td25)
        self.assertAlmostEqual(calc_hours(td25.tariff_schedule.mon_thu), 8.0)
        self.assertAlmostEqual(calc_hours(td25.tariff_schedule.sat), 8.0)

        # D45d (TD45_001) should have 20 hours of NT
        td45 = self.db.get("TD45_001")
        self.assertIsNotNone(td45)
        self.assertAlmostEqual(calc_hours(td45.tariff_schedule.mon_thu), 20.0)

        # D57d (TD57_001) should have 20 hours of NT
        td57 = self.db.get("TD57_001")
        self.assertIsNotNone(td57)
        self.assertAlmostEqual(calc_hours(td57.tariff_schedule.mon_thu), 20.0)

        # D35d (TD35_001) should have 16 hours of NT
        td35 = self.db.get("TD35_001")
        self.assertIsNotNone(td35)
        self.assertAlmostEqual(calc_hours(td35.tariff_schedule.mon_thu), 16.0)

    def test_custom_csv_loading(self) -> None:
        """Test loading database from custom CSV string."""
        sample_csv = (
            "ID TOU,PRE jméno,Tarify,Relé 1,Relé 2,Užití\n"
            "TEST_001,TOU TEST 1 2 3,101,102,103,1F/3F\n"
            "ID TOU,PRE jméno,ID,Po,Ut,St,Čt,Pa,So,Ne,Sv,Registry,Zap,Vyp,Zap,Vyp\n"
            "TEST_001,TOU TEST 1 2 3,10,,,,,,,,,101, - test note,,,,\n"
            ",,,x,x,x,x,,,,,,00:00:00,08:00:00,,\n"
            ",,,,,,,x,,,,,00:00:00,08:00:00,,\n"
            ",,,,,,,,x,,,,00:00:00,08:00:00,,\n"
            ",,,,,,,,,x,,,00:00:00,08:00:00,,\n"
            ",,,,,,,,,,x,,00:00:00,08:00:00,,\n"
        )
        custom_db = PreTouDatabase.from_csv_string(sample_csv)
        self.assertIn("TEST_001", custom_db.items)
        item = custom_db.get("TEST_001")
        self.assertEqual(item.pre_name, "TOU TEST 1 2 3")
        self.assertEqual(len(item.tariff_schedule.mon_thu), 1)
        self.assertEqual(item.tariff_schedule.mon_thu[0].start_str, "00:00:00")
        self.assertEqual(item.tariff_schedule.mon_thu[0].end_str, "08:00:00")


if __name__ == "__main__":
    unittest.main()
