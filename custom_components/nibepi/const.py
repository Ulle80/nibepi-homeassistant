"""Constants for the NibePi integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "nibepi"

CONF_BASE_TOPIC: Final = "base_topic"
CONF_LWT_TOPIC: Final = "lwt_topic"

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

SIGNAL_NEW_REGISTER: Final = "nibepi_new_register_{entry_id}"
SIGNAL_REGISTER_UPDATE: Final = "nibepi_register_update_{entry_id}_{register}"
SIGNAL_AVAILABILITY: Final = "nibepi_availability_{entry_id}"
