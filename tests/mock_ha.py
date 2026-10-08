"""Mock module for Home Assistant when running standalone tests."""

import sys
from types import ModuleType
from datetime import datetime, timezone


class MockDtUtil:
    DEFAULT_TIME_ZONE = timezone.utc

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    @staticmethod
    def as_utc(d):
        if d.tzinfo is None:
            return d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)


class SubscriptableMeta(type):
    def __getitem__(cls, item):
        return cls


class SubscriptableObject(metaclass=SubscriptableMeta):
    pass


class MockCoordinator(SubscriptableObject):
    def __init__(self, hass=None, *args, **kwargs):
        self.hass = hass


class MockCoordinatorEntity(SubscriptableObject):
    def __init__(self, coordinator=None, *args, **kwargs):
        self.coordinator = coordinator


class MockEntity:
    def __init__(self, *args, **kwargs):
        pass

    @property
    def unique_id(self):
        return getattr(self, "_attr_unique_id", None)


class MockConfigFlow:
    def __init_subclass__(cls, domain=None, **kwargs):
        cls.domain = domain
        super().__init_subclass__(**kwargs)

    def async_show_form(self, step_id=None, data_schema=None, errors=None, description_placeholders=None):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}

    def async_create_entry(self, title=None, data=None, description=None):
        return {"type": "create_entry", "title": title, "data": data or {}}

    async def async_set_unique_id(self, unique_id):
        self._unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        pass


def setup_ha_mocks():
    if "voluptuous" not in sys.modules:
        vol = ModuleType("voluptuous")
        vol.Schema = lambda schema: schema
        vol.Required = lambda key, default=None: key
        vol.Optional = lambda key, default=None: key
        vol.In = lambda container: lambda val: val
        sys.modules["voluptuous"] = vol

    if "homeassistant" in sys.modules and hasattr(sys.modules["homeassistant"], "_is_mock"):
        return

    ha = ModuleType("homeassistant")
    ha._is_mock = True

    ha_core = ModuleType("homeassistant.core")
    ha_core.HomeAssistant = object
    ha_core.CALLBACK_TYPE = object
    ha_core.callback = lambda f: f

    ha_config_entries = ModuleType("homeassistant.config_entries")
    ha_config_entries.ConfigEntry = object
    ha_config_entries.ConfigFlow = MockConfigFlow
    ha_config_entries.OptionsFlow = MockConfigFlow
    ha_config_entries.ConfigFlowResult = dict

    ha_util = ModuleType("homeassistant.util")
    ha_util.dt = MockDtUtil

    ha_helpers = ModuleType("homeassistant.helpers")
    ha_helpers_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
    ha_helpers_update_coordinator.DataUpdateCoordinator = MockCoordinator
    ha_helpers_update_coordinator.UpdateFailed = Exception
    ha_helpers_update_coordinator.CoordinatorEntity = MockCoordinatorEntity

    ha_helpers_event = ModuleType("homeassistant.helpers.event")
    ha_helpers_event.async_track_point_in_utc_time = lambda *args: None

    ha_helpers_device = ModuleType("homeassistant.helpers.device_registry")
    ha_helpers_device.DeviceEntryType = type("DeviceEntryType", (), {"SERVICE": "service"})
    ha_helpers_device.DeviceInfo = dict

    ha_helpers_entity_platform = ModuleType("homeassistant.helpers.entity_platform")
    ha_helpers_entity_platform.AddEntitiesCallback = object

    ha_helpers_selector = ModuleType("homeassistant.helpers.selector")
    ha_helpers_selector.SelectSelector = lambda *args, **kwargs: None
    ha_helpers_selector.SelectSelectorConfig = lambda *args, **kwargs: None
    ha_helpers_selector.SelectSelectorMode = type("SelectSelectorMode", (), {"DROPDOWN": "dropdown"})
    ha_helpers_selector.SelectOptionDict = dict
    ha_helpers_selector.BooleanSelector = lambda *args, **kwargs: None
    ha_helpers_selector.TextSelector = lambda *args, **kwargs: None
    ha_helpers_selector.TextSelectorConfig = lambda *args, **kwargs: None

    ha_components = ModuleType("homeassistant.components")
    ha_binary_sensor = ModuleType("homeassistant.components.binary_sensor")
    ha_binary_sensor.BinarySensorEntity = MockEntity
    ha_binary_sensor.BinarySensorEntityDescription = lambda **kwargs: type("Description", (), kwargs)()

    ha_sensor = ModuleType("homeassistant.components.sensor")
    ha_sensor.SensorEntity = MockEntity
    ha_sensor.SensorEntityDescription = lambda **kwargs: type("Description", (), kwargs)()
    ha_sensor.SensorDeviceClass = type("SensorDeviceClass", (), {"TIMESTAMP": "timestamp"})

    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.config_entries"] = ha_config_entries
    sys.modules["homeassistant.util"] = ha_util
    sys.modules["homeassistant.util.dt"] = MockDtUtil
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_helpers_update_coordinator
    sys.modules["homeassistant.helpers.event"] = ha_helpers_event
    sys.modules["homeassistant.helpers.device_registry"] = ha_helpers_device
    sys.modules["homeassistant.helpers.entity_platform"] = ha_helpers_entity_platform
    sys.modules["homeassistant.helpers.selector"] = ha_helpers_selector
    sys.modules["homeassistant.components"] = ha_components
    sys.modules["homeassistant.components.binary_sensor"] = ha_binary_sensor
    sys.modules["homeassistant.components.sensor"] = ha_sensor


setup_ha_mocks()
