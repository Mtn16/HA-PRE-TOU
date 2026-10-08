"""Binary sensor platform for PRE TOU integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENABLE_RELAYS, CONF_TOU_ID, DEFAULT_ENABLE_RELAYS, DOMAIN
from .coordinator import PreTouCoordinator

BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="vt_active",
        name="Vysoký tarif (VT)",
        translation_key="vt_active",
        icon="mdi:flash",
    ),
    BinarySensorEntityDescription(
        key="nt_active",
        name="Nízký tarif (NT)",
        translation_key="nt_active",
        icon="mdi:cash-clock",
    ),
    BinarySensorEntityDescription(
        key="rele1_active",
        name="Relé 1",
        translation_key="rele1_active",
        icon="mdi:electric-switch",
    ),
    BinarySensorEntityDescription(
        key="rele2_active",
        name="Relé 2",
        translation_key="rele2_active",
        icon="mdi:electric-switch",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PRE TOU binary sensors from a config entry."""
    coordinator: PreTouCoordinator = hass.data[DOMAIN][entry.entry_id]

    enable_relays: bool = entry.options.get(
        CONF_ENABLE_RELAYS, entry.data.get(CONF_ENABLE_RELAYS, DEFAULT_ENABLE_RELAYS)
    )

    entities: list[PreTouBinarySensor] = []

    for description in BINARY_SENSOR_DESCRIPTIONS:
        if description.key == "rele1_active" and not enable_relays:
            continue
        if description.key == "rele2_active":
            if not enable_relays or not coordinator.data.get("rele2_applicable", True):
                continue

        entities.append(
            PreTouBinarySensor(
                coordinator=coordinator,
                entry=entry,
                description=description,
            )
        )

    async_add_entities(entities)


class PreTouBinarySensor(CoordinatorEntity[PreTouCoordinator], BinarySensorEntity):
    """Binary sensor for PRE TOU state."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PreTouCoordinator,
        entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return bool(self.coordinator.data.get(self.entity_description.key, False))
