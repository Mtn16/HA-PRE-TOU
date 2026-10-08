"""Tests for PRE TOU coordinator and entity creation."""

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

import tests.mock_ha
from custom_components.pre_tou.const import (
    CONF_ENABLE_RELAYS,
    CONF_PHASE,
    CONF_TOU_ID,
    DOMAIN,
    PHASE_1F,
    PHASE_3F,
)
from custom_components.pre_tou.coordinator import PreTouCoordinator
from custom_components.pre_tou.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    PreTouBinarySensor,
)
from custom_components.pre_tou.sensor import (
    TIMESTAMP_SENSOR_DESCRIPTIONS,
    TARIFF_SENSOR_DESCRIPTION,
    PreTouTimestampSensor,
    PreTouTariffSensor,
)


class TestCoordinatorAndEntities(unittest.TestCase):
    """Test coordinator data processing and entity values."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.hass = MagicMock()
        self.entry = MagicMock()
        self.entry.entry_id = "test_entry_123"
        self.entry.data = {
            CONF_TOU_ID: "TD25_001",
            CONF_PHASE: PHASE_3F,
            CONF_ENABLE_RELAYS: True,
        }
        self.entry.options = {}

    def test_coordinator_calculation(self) -> None:
        """Test coordinator _async_update_data calculation."""
        coordinator = PreTouCoordinator(self.hass, self.entry)

        # Mock current time to Wednesday 15:05 Prague time (13:05 UTC)
        mock_now = datetime(2026, 10, 7, 13, 5, 0, tzinfo=timezone.utc)
        with patch("homeassistant.util.dt.now", return_value=mock_now.astimezone()):
            import asyncio
            data = asyncio.run(coordinator._async_update_data())

        self.assertIn("vt_active", data)
        self.assertIn("nt_active", data)
        self.assertIn("next_vt", data)
        self.assertIn("next_nt", data)
        self.assertIn("current_tariff", data)
        self.assertIn("rele1_active", data)
        self.assertIn("rele2_active", data)
        self.assertIn("attributes", data)

        self.assertEqual(data["attributes"]["tou_id"], "TD25_001")
        self.assertEqual(data["attributes"]["phase"], "3F")

    def test_binary_sensor_entities(self) -> None:
        """Test binary sensor values based on coordinator data."""
        coordinator = MagicMock()
        coordinator.data = {
            "vt_active": False,
            "nt_active": True,
            "rele1_active": True,
            "rele2_active": False,
        }
        coordinator.tou_item = MagicMock()
        coordinator.tou_item.pre_name = "TOU 503 504 504"

        # VT sensor
        vt_desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "vt_active")
        vt_sensor = PreTouBinarySensor(coordinator, self.entry, vt_desc)
        self.assertFalse(vt_sensor.is_on)
        self.assertEqual(vt_sensor.unique_id, "test_entry_123_vt_active")

        # NT sensor
        nt_desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "nt_active")
        nt_sensor = PreTouBinarySensor(coordinator, self.entry, nt_desc)
        self.assertTrue(nt_sensor.is_on)
        self.assertEqual(nt_sensor.unique_id, "test_entry_123_nt_active")

    def test_sensor_entities(self) -> None:
        """Test sensor values based on coordinator data."""
        dt_nt = datetime(2026, 10, 8, 1, 0, tzinfo=timezone.utc)
        dt_vt = datetime(2026, 10, 7, 16, 0, tzinfo=timezone.utc)
        coordinator = MagicMock()
        coordinator.data = {
            "current_tariff": "NT",
            "next_nt": dt_nt,
            "next_vt": dt_vt,
            "attributes": {"tou_id": "TD25_001", "is_holiday": False},
        }
        coordinator.tou_item = MagicMock()
        coordinator.tou_item.pre_name = "TOU 503 504 504"

        # Tariff sensor
        tariff_sensor = PreTouTariffSensor(coordinator, self.entry, TARIFF_SENSOR_DESCRIPTION)
        self.assertEqual(tariff_sensor.native_value, "NT")
        self.assertEqual(tariff_sensor.extra_state_attributes["tou_id"], "TD25_001")

        # Next NT timestamp sensor
        next_nt_desc = next(d for d in TIMESTAMP_SENSOR_DESCRIPTIONS if d.key == "next_nt")
        next_nt_sensor = PreTouTimestampSensor(coordinator, self.entry, next_nt_desc)
        self.assertEqual(next_nt_sensor.native_value, dt_nt)

        # Next VT timestamp sensor
        next_vt_desc = next(d for d in TIMESTAMP_SENSOR_DESCRIPTIONS if d.key == "next_vt")
        next_vt_sensor = PreTouTimestampSensor(coordinator, self.entry, next_vt_desc)
        self.assertEqual(next_vt_sensor.native_value, dt_vt)


if __name__ == "__main__":
    unittest.main()
