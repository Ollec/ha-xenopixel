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
LIGHT_EFFECT_MIN: Final = 1
LIGHT_EFFECT_MAX: Final = 9
PARAM_VOLUME: Final = "Volume"

# Combat effects (confirmed via BLE capture 2026-01-31)
# One-shot effects (trigger once, no notification feedback)
PARAM_CLASH: Final = "Clash"
PARAM_BLASTER: Final = "Blaster"
PARAM_FORCE: Final = "Force"

# Toggled effects (stay active until explicitly turned off, send notifications)
PARAM_LOCKUP: Final = "Lockup"
PARAM_DRAG: Final = "Drag"

# Combat effect status fields (from full status dump)
PARAM_CURRENT_LOCKUP: Final = "CurrentLockup"
PARAM_TOTAL_LOCKUP: Final = "TotalLockup"
PARAM_CURRENT_DRAG: Final = "CurrentDrag"
PARAM_TOTAL_DRAG: Final = "TotalDrag"
PARAM_CURRENT_BLASTER: Final = "CurrentBlaster"
PARAM_TOTAL_BLASTER: Final = "TotalBlaster"
PARAM_CURRENT_CLASH: Final = "CurrentClash"
PARAM_TOTAL_CLASH: Final = "TotalClash"
PARAM_CURRENT_FORCE: Final = "CurrentForce"
PARAM_TOTAL_FORCE: Final = "TotalForce"

# Additional status fields
PARAM_TOTAL_LIGHT_EFFECTS: Final = "TotalLightEffect"
PARAM_CURRENT_POST_OFF: Final = "CurrentPostOff"
PARAM_TOTAL_POST_OFF: Final = "TotalPostOff"
PARAM_CURRENT_MODE: Final = "CurrentMode"
PARAM_TOTAL_MODE: Final = "TotalMode"
PARAM_PREON_TIME: Final = "PreonTime"

# Timeouts
COMMAND_TIMEOUT: Final = 5.0  # seconds
NOTIFICATION_TIMEOUT: Final = 2.0  # seconds
