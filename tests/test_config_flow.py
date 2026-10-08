"""Tests for PRE TOU config flow."""

import unittest
from unittest.mock import MagicMock, patch

import tests.mock_ha
from custom_components.pre_tou.config_flow import PreTouConfigFlow, PreTouOptionsFlow
from custom_components.pre_tou.const import (
    CONF_CUSTOM_CSV,
    CONF_ENABLE_RELAYS,
    CONF_PHASE,
    CONF_TOU_ID,
    DOMAIN,
    PHASE_3F,
)


class TestPreTouConfigFlow(unittest.TestCase):
    """Test config flow."""

    def test_show_user_form(self) -> None:
        """Test showing the user step form."""
        flow = PreTouConfigFlow()
        flow.hass = MagicMock()

        import asyncio
        result = asyncio.run(flow.async_step_user(user_input=None))

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")
        self.assertEqual(result["errors"], {})

    def test_submit_valid_tou_id(self) -> None:
        """Test submitting a valid TOU ID."""
        flow = PreTouConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = MagicMock(return_value=asyncio_return(None))
        flow._abort_if_unique_id_configured = MagicMock()

        import asyncio
        user_input = {
            CONF_TOU_ID: "TD25_001",
            CONF_PHASE: PHASE_3F,
            CONF_ENABLE_RELAYS: True,
            CONF_CUSTOM_CSV: "",
        }
        result = asyncio.run(flow.async_step_user(user_input=user_input))

        self.assertEqual(result["type"], "create_entry")
        self.assertIn("TD25_001", result["title"])
        self.assertEqual(result["data"][CONF_TOU_ID], "TD25_001")

    def test_submit_invalid_tou_id(self) -> None:
        """Test submitting an unknown TOU ID."""
        flow = PreTouConfigFlow()
        flow.hass = MagicMock()

        import asyncio
        user_input = {
            CONF_TOU_ID: "NON_EXISTENT_999",
            CONF_PHASE: PHASE_3F,
            CONF_ENABLE_RELAYS: True,
            CONF_CUSTOM_CSV: "",
        }
        result = asyncio.run(flow.async_step_user(user_input=user_input))

        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_TOU_ID, result["errors"])
        self.assertEqual(result["errors"][CONF_TOU_ID], "unknown_tou_id")

    def test_submit_invalid_custom_csv(self) -> None:
        """Test submitting malformed custom CSV."""
        flow = PreTouConfigFlow()
        flow.hass = MagicMock()

        import asyncio
        user_input = {
            CONF_TOU_ID: "TD25_001",
            CONF_PHASE: PHASE_3F,
            CONF_ENABLE_RELAYS: True,
            CONF_CUSTOM_CSV: "this,is,garbage,not,a,valid,pre,table",
        }
        result = asyncio.run(flow.async_step_user(user_input=user_input))

        self.assertEqual(result["type"], "form")
        self.assertIn(CONF_CUSTOM_CSV, result["errors"])


    def test_options_flow(self) -> None:
        """Test options flow."""
        config_entry = MagicMock()
        config_entry.data = {
            CONF_TOU_ID: "TD25_001",
            CONF_PHASE: PHASE_3F,
            CONF_ENABLE_RELAYS: True,
        }
        config_entry.options = {}

        options_flow = PreTouOptionsFlow(config_entry)
        options_flow.hass = MagicMock()

        import asyncio
        result = asyncio.run(options_flow.async_step_init(user_input=None))
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "init")

        # Submit change
        new_input = {
            CONF_TOU_ID: "TD25_002",
            CONF_PHASE: PHASE_3F,
            CONF_ENABLE_RELAYS: False,
            CONF_CUSTOM_CSV: "",
        }
        res_submit = asyncio.run(options_flow.async_step_init(user_input=new_input))
        self.assertEqual(res_submit["type"], "create_entry")
        self.assertEqual(res_submit["data"][CONF_TOU_ID], "TD25_002")


async def asyncio_return(val):
    return val


if __name__ == "__main__":
    unittest.main()
