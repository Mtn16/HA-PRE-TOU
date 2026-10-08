"""Sensor platform for PRE TOU integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENABLE_RELAYS, CONF_TOU_ID, DEFAULT_ENABLE_RELAYS, DOMAIN
from .coordinator import PreTouCoordinator

TIMESTAMP_SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="next_vt",
        name="Další spuštění VT",
        translation_key="next_vt",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
    ),
    SensorEntityDescription(
        key="next_nt",
        name="Další spuštění NT",
        translation_key="next_nt",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
    ),
    SensorEntityDescription(
        key="next_rele1",
        name="Další sepnutí Relé 1",
        translation_key="next_rele1",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
    ),
    SensorEntityDescription(
        key="next_rele2",
        name="Další sepnutí Relé 2",
        translation_key="next_rele2",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
    ),
)

TARIFF_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="current_tariff",
    name="Aktuální tarif",
    translation_key="current_tariff",
    icon="mdi:cash-clock",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PRE TOU sensors from a config entry."""
    coordinator: PreTouCoordinator = hass.data[DOMAIN][entry.entry_id]

    enable_relays: bool = entry.options.get(
        CONF_ENABLE_RELAYS, entry.data.get(CONF_ENABLE_RELAYS, DEFAULT_ENABLE_RELAYS)
    )

    entities: list[SensorEntity] = []

    # Current Tariff sensor
    entities.append(
        PreTouTariffSensor(
            coordinator=coordinator,
            entry=entry,
            description=TARIFF_SENSOR_DESCRIPTION,
        )
    )

    # Next start timestamp sensors
    for description in TIMESTAMP_SENSOR_DESCRIPTIONS:
        if description.key == "next_rele1" and not enable_relays:
            continue
        if description.key == "next_rele2":
            if not enable_relays or not coordinator.data.get("rele2_applicable", True):
                continue

        entities.append(
            PreTouTimestampSensor(
                coordinator=coordinator,
                entry=entry,
                description=description,
            )
        )

    async_add_entities(entities)


class PreTouTimestampSensor(CoordinatorEntity[PreTouCoordinator], SensorEntity):
    """Timestamp sensor for next switch times."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PreTouCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        tou_id = entry.data.get(CONF_TOU_ID, "")
        pre_name = (
            coordinator.tou_item.pre_name
            if coordinator.tou_item and coordinator.tou_item.pre_name
            else "TOU"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"PRE TOU ({tou_id})",
            manufacturer="PREdistribuce",
            model=pre_name,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the next switch timestamp in UTC."""
        val = self.coordinator.data.get(self.entity_description.key)
        if isinstance(val, datetime):
            return val
        return None


class PreTouTariffSensor(CoordinatorEntity[PreTouCoordinator], SensorEntity):
    """Sensor displaying current tariff (VT or NT) with detailed schedule attributes."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PreTouCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        tou_id = entry.data.get(CONF_TOU_ID, "")
        pre_name = (
            coordinator.tou_item.pre_name
            if coordinator.tou_item and coordinator.tou_item.pre_name
            else "TOU"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"PRE TOU ({tou_id})",
            manufacturer="PREdistribuce",
            model=pre_name,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> str | None:
        """Return VT or NT."""
        return self.coordinator.data.get("current_tariff")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return rich schedule attributes."""
        return self.coordinator.data.get("attributes", {})
