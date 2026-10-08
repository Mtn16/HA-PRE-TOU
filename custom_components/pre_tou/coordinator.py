"""DataUpdateCoordinator for PRE TOU integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CURRENT_TARIFF,
    ATTR_DAY_TYPE,
    ATTR_IS_HOLIDAY,
    ATTR_PRE_NAME,
    ATTR_RELE1_REG,
    ATTR_RELE2_REG,
    ATTR_TARIFF_REG,
    ATTR_TODAY_INTERVALS,
    ATTR_TOMORROW_INTERVALS,
    ATTR_TOU_ID,
    ATTR_USAGE,
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
from .parser import (
    DaySchedule,
    PreTouDatabase,
    TouItem,
    calculate_schedule_state,
)

_LOGGER = logging.getLogger(__name__)


def get_default_csv_path() -> str:
    """Get the path to the bundled pre_tou_data.csv file."""
    return os.path.join(os.path.dirname(__file__), "data", "pre_tou_data.csv")


def load_database(custom_csv: str | None = None) -> PreTouDatabase:
    """Load PreTouDatabase from custom CSV or bundled CSV."""
    if custom_csv and custom_csv.strip():
        _LOGGER.debug("Loading PRE TOU database from custom CSV")
        return PreTouDatabase.from_csv_string(custom_csv)

    default_path = get_default_csv_path()
    if os.path.exists(default_path):
        _LOGGER.debug("Loading PRE TOU database from bundled CSV: %s", default_path)
        return PreTouDatabase.from_csv_file(default_path)

    _LOGGER.error("PRE TOU bundled CSV not found at %s", default_path)
    return PreTouDatabase()


class PreTouCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching and calculating PRE TOU data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data.get(CONF_TOU_ID, 'unknown')}",
            update_interval=timedelta(seconds=60),
        )
        self.entry = entry
        self.tou_id: str = entry.data.get(CONF_TOU_ID, "")
        self.phase: str = entry.options.get(
            CONF_PHASE, entry.data.get(CONF_PHASE, DEFAULT_PHASE)
        )
        self.enable_relays: bool = entry.options.get(
            CONF_ENABLE_RELAYS,
            entry.data.get(CONF_ENABLE_RELAYS, DEFAULT_ENABLE_RELAYS),
        )
        self.custom_csv: str | None = entry.options.get(
            CONF_CUSTOM_CSV, entry.data.get(CONF_CUSTOM_CSV)
        )

        self.db: PreTouDatabase = load_database(self.custom_csv)
        self.tou_item: TouItem | None = self.db.get(self.tou_id)

        self._unsub_transition: CALLBACK_TYPE | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Compute the current and upcoming states."""
        if not self.tou_item:
            # Re-attempt finding item in DB
            self.tou_item = self.db.get(self.tou_id)
            if not self.tou_item:
                raise UpdateFailed(f"TOU ID {self.tou_id} not found in PRE database")

        now = dt_util.now()

        # 1. Tariff state (active = NT, inactive = VT)
        tariff_res = calculate_schedule_state(self.tou_item.tariff_schedule, now)
        is_nt_active = tariff_res["is_active"]
        is_vt_active = not is_nt_active

        next_nt = (
            dt_util.as_utc(tariff_res["next_start"])
            if tariff_res["next_start"]
            else None
        )
        next_vt = (
            dt_util.as_utc(tariff_res["next_end"])
            if tariff_res["next_end"]
            else None
        )

        upcoming_transitions: list[datetime] = []
        if tariff_res["next_transition"]:
            upcoming_transitions.append(tariff_res["next_transition"])

        # 2. Relay 1 state
        rele1_res: dict[str, Any] | None = None
        rele1_active = False
        next_rele1: datetime | None = None
        if self.enable_relays:
            rele1_res = calculate_schedule_state(self.tou_item.rele1_schedule, now)
            rele1_active = rele1_res["is_active"]
            if rele1_res["next_start"]:
                next_rele1 = dt_util.as_utc(rele1_res["next_start"])
            if rele1_res["next_transition"]:
                upcoming_transitions.append(rele1_res["next_transition"])

        # 3. Relay 2 state
        rele2_res: dict[str, Any] | None = None
        rele2_active = False
        next_rele2: datetime | None = None
        # Check if Relay 2 is applicable for current phase
        rele2_applicable = True
        if self.phase == PHASE_1F and self.tou_item.rele2_note == "1F_omit":
            rele2_applicable = False
        elif self.phase == PHASE_1F and self.tou_item.rele2_note == "3F_only":
            rele2_applicable = False

        if self.enable_relays and rele2_applicable:
            rele2_res = calculate_schedule_state(self.tou_item.rele2_schedule, now)
            rele2_active = rele2_res["is_active"]
            if rele2_res["next_start"]:
                next_rele2 = dt_util.as_utc(rele2_res["next_start"])
            if rele2_res["next_transition"]:
                upcoming_transitions.append(rele2_res["next_transition"])

        # Schedule exact wakeup at the next transition
        self._schedule_next_transition_wakeup(upcoming_transitions)

        return {
            "vt_active": is_vt_active,
            "nt_active": is_nt_active,
            "next_vt": next_vt,
            "next_nt": next_nt,
            "current_tariff": "NT" if is_nt_active else "VT",
            "rele1_active": rele1_active,
            "next_rele1": next_rele1,
            "rele2_active": rele2_active,
            "next_rele2": next_rele2,
            "rele2_applicable": rele2_applicable,
            "attributes": {
                ATTR_TOU_ID: self.tou_item.tou_id,
                ATTR_PRE_NAME: self.tou_item.pre_name,
                ATTR_TARIFF_REG: self.tou_item.tariff_reg,
                ATTR_RELE1_REG: self.tou_item.rele1_reg,
                ATTR_RELE2_REG: self.tou_item.rele2_reg,
                ATTR_USAGE: self.tou_item.usage,
                CONF_PHASE: self.phase,
                ATTR_IS_HOLIDAY: tariff_res["is_holiday"],
                ATTR_DAY_TYPE: tariff_res["day_type"],
                ATTR_TODAY_INTERVALS: tariff_res["today_intervals"],
                ATTR_TOMORROW_INTERVALS: tariff_res["tomorrow_intervals"],
            },
        }

    def _schedule_next_transition_wakeup(
        self, upcoming_transitions: list[datetime]
    ) -> None:
        """Schedule an exact update right after the next transition occurs."""
        if self._unsub_transition:
            self._unsub_transition()
            self._unsub_transition = None

        if not upcoming_transitions:
            return

        earliest = min(upcoming_transitions)
        # Wake up 1 second after the transition to avoid race condition on the boundary
        wake_up_time = dt_util.as_utc(earliest) + timedelta(seconds=1)

        @callback
        def _wakeup(now: datetime) -> None:
            self._unsub_transition = None
            self.hass.async_create_task(self.async_refresh())

        self._unsub_transition = async_track_point_in_utc_time(
            self.hass, _wakeup, wake_up_time
        )

    def async_unload(self) -> None:
        """Clean up resources on unload."""
        if self._unsub_transition:
            self._unsub_transition()
            self._unsub_transition = None
