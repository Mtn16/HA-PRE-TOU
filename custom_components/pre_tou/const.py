"""Constants for the PRE TOU integration."""

DOMAIN = "pre_tou"

# Configuration options
CONF_TOU_ID = "tou_id"
CONF_PHASE = "phase"
CONF_ENABLE_RELAYS = "enable_relays"
CONF_CUSTOM_CSV = "custom_csv"

# Phase options
PHASE_1F = "1F"
PHASE_3F = "3F"
PHASE_OPTIONS = [PHASE_3F, PHASE_1F]

DEFAULT_PHASE = PHASE_3F
DEFAULT_ENABLE_RELAYS = True

# Platforms
PLATFORMS = ["binary_sensor", "sensor"]

# Attributes
ATTR_TOU_ID = "tou_id"
ATTR_PRE_NAME = "pre_name"
ATTR_TARIFF_REG = "tariff_register"
ATTR_RELE1_REG = "rele1_register"
ATTR_RELE2_REG = "rele2_register"
ATTR_USAGE = "usage"
ATTR_CURRENT_TARIFF = "current_tariff"
ATTR_IS_HOLIDAY = "is_holiday"
ATTR_DAY_TYPE = "day_type"
ATTR_TODAY_INTERVALS = "today_intervals"
ATTR_TOMORROW_INTERVALS = "tomorrow_intervals"
ATTR_NEXT_TRANSITION = "next_transition"
ATTR_NEXT_VT = "next_vt"
ATTR_NEXT_NT = "next_nt"
ATTR_NEXT_RELE1 = "next_rele1"
ATTR_NEXT_RELE2 = "next_rele2"
