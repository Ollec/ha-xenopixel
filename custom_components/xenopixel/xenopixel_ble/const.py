"""BLE constants for Xenopixel protocol."""

from __future__ import annotations

from typing import Final

# GATT Service and Characteristic UUIDs
# Discovered via nRF Connect on 2026-01-28
# Protocol: JSON-based messages over BLE

# Primary control service (JSON protocol)
SERVICE_UUID: Final = "0000dae0-0000-1000-8000-00805f9b34fb"  # Short: 0xDAE0
CHAR_CONTROL_UUID: Final = "0000dae1-0000-1000-8000-00805f9b34fb"  # NOTIFY, READ, WRITE

# Secondary control service (alternative channel)
SERVICE_UUID_ALT: Final = "00003ab0-0000-1000-8000-00805f9b34fb"  # Short: 0x3AB0
CHAR_CONTROL_ALT_UUID: Final = (
    "00003ab1-0000-1000-8000-00805f9b34fb"  # WRITE NO RESPONSE
)

# JSON Message Types (confirmed via HCI snoop capture 2026-01-28)
# Commands TO device use type 2, Notifications FROM device use type 3
MSG_TYPE_COMMAND: Final = 2  # For write commands TO device
MSG_TYPE_STATUS: Final = 3  # For notifications FROM device

# Known JSON parameter keys (confirmed via nRF Logger capture)
# Power control (blade on/off)
PARAM_POWER_ON: Final = "PowerOn"  # boolean: true = ignite, false = retract

# Battery level (status only, not a command)
PARAM_POWER: Final = "Power"  # int: battery percentage (e.g., 63 = 63%)

# Color control
PARAM_BACKGROUND_COLOR: Final = "BackgroundColor"  # array: [R, G, B] (0-255 each)

# Brightness control
PARAM_BRIGHTNESS: Final = "Brightness"  # int: brightness level

# Authorization handshake (confirmed via HCI snoop 2026-01-30)
# The client must actively send these two messages after connecting:
#   1. [2,{"HandShake":"HelloDamien"}] → written to DAE1 (Write Request)
#   2. [2,{"Authorize":"SaberOfDamien"}] → written to 3AB1 (Write Command)
# The saber responds with [3,{"Authorize":"AccessAllowed"}] on 3AB1
PARAM_HANDSHAKE: Final = "HandShake"
HANDSHAKE_VALUE: Final = "HelloDamien"
PARAM_AUTHORIZE: Final = "Authorize"
AUTHORIZE_VALUE: Final = "SaberOfDamien"
AUTHORIZE_RESPONSE: Final = "AccessAllowed"

# Status fields (received in notifications)
PARAM_HARDWARE_VERSION: Final = "HardwareVersion"
PARAM_SOFTWARE_VERSION: Final = "SoftwareVersion"
PARAM_CURRENT_SOUND_PACKAGE: Final = "CurrentSoundPackageNo"
PARAM_TOTAL_SOUND_PACKAGES: Final = "TotalSoundPackage"
PARAM_CURRENT_LIGHT_EFFECT: Final = "CurrentLightEffect"
PARAM_VOLUME: Final = "Volume"

# Timeouts
COMMAND_TIMEOUT: Final = 5.0  # seconds
NOTIFICATION_TIMEOUT: Final = 2.0  # seconds
