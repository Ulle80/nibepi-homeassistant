"""Constants for the NibePi integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "nibepi"

CONF_BASE_TOPIC: Final = "base_topic"
CONF_LWT_TOPIC: Final = "lwt_topic"
CONF_LANGUAGE: Final = "language"
CONF_MODEL: Final = "model"
MODEL_AUTO: Final = "auto"
DEFAULT_DEVICE_MODEL: Final = "Heat pump (via NibePi)"

# NibePi defaults (see default.json in anerdins/nibepi).
DEFAULT_BASE_TOPIC: Final = "nibe/modbus/"
# NibePi hardcodes its MQTT last-will topic to "nibe", payload "<client_id> disconnected".
DEFAULT_LWT_TOPIC: Final = "nibe"
LWT_DISCONNECTED_SUFFIX: Final = "disconnected"

# Per register NibePi publishes:
#   <base><register>        scaled value (plain text, or mapped label)
#   <base><register>/raw    unscaled integer
#   <base><register>/json   full register object incl. metadata
#   <base><register>/set    (subscribed by NibePi) write a value
TOPIC_SUFFIX_JSON: Final = "/json"
TOPIC_SUFFIX_SET: Final = "/set"
TOPIC_SUFFIX_GET: Final = "/get"

# NibePi does not retain its messages. Known register definitions are stored so
# entities come back after a restart, and values are actively requested.
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "nibepi.{entry_id}"
STORAGE_SAVE_DELAY: Final = 10
# Pause between /get requests so the RS485 bus is not flooded.
REFRESH_REQUEST_DELAY: Final = 0.25

# Writable registers are created disabled, except these everyday comfort
# settings (NIBE F-series register numbers). Everything else that can change
# the heat pump's behaviour (operating mode, degree minutes, pump speeds,
# additive heat ...) must be enabled deliberately by the user.
COMFORT_REGISTERS: Final = frozenset(
    {
        "47007", "47008", "47009", "47010",  # heat curve S1-S4
        "47011", "47012", "47013", "47014",  # heat curve offset S1-S4
        "47398", "47397", "47396", "47395",  # room setpoint S1-S4
        "47041",  # hot water comfort mode
        "48132", "10020",  # temporary lux (extra hot water)
    }
)  # fmt: skip

SIGNAL_NEW_REGISTER: Final = "nibepi_new_register_{entry_id}"
SIGNAL_REGISTER_UPDATE: Final = "nibepi_register_update_{entry_id}_{register}"
SIGNAL_AVAILABILITY: Final = "nibepi_availability_{entry_id}"
