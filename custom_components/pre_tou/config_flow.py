"""Config flow for PRE TOU integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CUSTOM_CSV,
    CONF_ENABLE_RELAYS,
    CONF_PHASE,
    CONF_TOU_ID,
    DEFAULT_ENABLE_RELAYS,
    DEFAULT_PHASE,
    DOMAIN,
    PHASE_1F,
    PHASE_3F,
)
from .coordinator import load_database
from .parser import PreTouDatabase

_LOGGER = logging.getLogger(__name__)


class PreTouConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PRE TOU."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._db: PreTouDatabase = load_database()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            custom_csv = user_input.get(CONF_CUSTOM_CSV, "").strip()
            tou_id = user_input.get(CONF_TOU_ID, "").strip()

            active_db = self._db
            if custom_csv:
                try:
                    custom_db = PreTouDatabase.from_csv_string(custom_csv)
                    if not custom_db.items:
                        errors[CONF_CUSTOM_CSV] = "invalid_csv"
                    else:
                        active_db = custom_db
                except Exception:
                    errors[CONF_CUSTOM_CSV] = "invalid_csv"

            if not errors:
                if not active_db.get(tou_id):
                    errors[CONF_TOU_ID] = "unknown_tou_id"

            if not errors:
                await self.async_set_unique_id(f"pre_tou_{tou_id}")
                self._abort_if_unique_id_configured()

                item = active_db.get(tou_id)
                title = f"PRE TOU ({tou_id})"
                if item and item.pre_name:
                    title = f"PRE TOU {tou_id} - {item.pre_name}"

                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        options = self._db.list_options()
        select_options = [
            selector.SelectOptionDict(value=tid, label=label)
            for tid, label in options
        ]

        # Default to TD25_001 if available, else first option
        default_tou = "TD25_001"
        if not any(opt["value"] == default_tou for opt in select_options) and select_options:
            default_tou = select_options[0]["value"]

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TOU_ID, default=default_tou): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=select_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                    )
                ),
                vol.Required(CONF_PHASE, default=DEFAULT_PHASE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=PHASE_3F, label="Třífázový (3F)"
                            ),
                            selector.SelectOptionDict(
                                value=PHASE_1F, label="Jednofázový (1F)"
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_ENABLE_RELAYS, default=DEFAULT_ENABLE_RELAYS
                ): selector.BooleanSelector(),
                vol.Optional(CONF_CUSTOM_CSV, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PreTouOptionsFlow:
        """Get the options flow handler."""
        return PreTouOptionsFlow(config_entry)


class PreTouOptionsFlow(OptionsFlow):
    """Handle options for PRE TOU."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._db: PreTouDatabase = load_database(
            config_entry.options.get(
                CONF_CUSTOM_CSV, config_entry.data.get(CONF_CUSTOM_CSV)
            )
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            custom_csv = user_input.get(CONF_CUSTOM_CSV, "").strip()
            tou_id = user_input.get(CONF_TOU_ID, "").strip()

            active_db = self._db
            if custom_csv:
                try:
                    custom_db = PreTouDatabase.from_csv_string(custom_csv)
                    if not custom_db.items:
                        errors[CONF_CUSTOM_CSV] = "invalid_csv"
                    else:
                        active_db = custom_db
                except Exception:
                    errors[CONF_CUSTOM_CSV] = "invalid_csv"

            if not errors:
                if not active_db.get(tou_id):
                    errors[CONF_TOU_ID] = "unknown_tou_id"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        current_tou = self.config_entry.options.get(
            CONF_TOU_ID, self.config_entry.data.get(CONF_TOU_ID, "TD25_001")
        )
        current_phase = self.config_entry.options.get(
            CONF_PHASE, self.config_entry.data.get(CONF_PHASE, DEFAULT_PHASE)
        )
        current_relays = self.config_entry.options.get(
            CONF_ENABLE_RELAYS,
            self.config_entry.data.get(CONF_ENABLE_RELAYS, DEFAULT_ENABLE_RELAYS),
        )
        current_csv = self.config_entry.options.get(
            CONF_CUSTOM_CSV, self.config_entry.data.get(CONF_CUSTOM_CSV, "")
        )

        options = self._db.list_options()
        select_options = [
            selector.SelectOptionDict(value=tid, label=label)
            for tid, label in options
        ]

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TOU_ID, default=current_tou): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=select_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                    )
                ),
                vol.Required(CONF_PHASE, default=current_phase): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=PHASE_3F, label="Třífázový (3F)"
                            ),
                            selector.SelectOptionDict(
                                value=PHASE_1F, label="Jednofázový (1F)"
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_ENABLE_RELAYS, default=current_relays
                ): selector.BooleanSelector(),
                vol.Optional(CONF_CUSTOM_CSV, default=current_csv): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
