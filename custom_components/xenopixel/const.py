"""Constants for the Xenopixel Lightsaber integration."""

from __future__ import annotations

from typing import Final

# Integration domain
DOMAIN: Final = "xenopixel"

# Default values
DEFAULT_NAME: Final = "Xenopixel Saber"

# Configuration keys
CONF_DEVICE_NAME: Final = "device_name"
CONF_MAC_ADDRESS: Final = "mac_address"

# BLE UUIDs (discovered via nRF Connect 2026-01-28)
# Primary control service - uses JSON protocol
SERVICE_UUID: Final = "0000dae0-0000-1000-8000-00805f9b34fb"  # Short: 0xDAE0
CHAR_CONTROL_UUID: Final = "0000dae1-0000-1000-8000-00805f9b34fb"  # NOTIFY, READ, WRITE

# Secondary control service (alternative channel)
SERVICE_UUID_ALT: Final = "00003ab0-0000-1000-8000-00805f9b34fb"  # Short: 0x3AB0
CHAR_CONTROL_ALT_UUID: Final = (
    "00003ab1-0000-1000-8000-00805f9b34fb"  # NOTIFY, READ, WRITE NO RESPONSE
)

# Connection settings
CONNECTION_TIMEOUT: Final = 10.0  # seconds
SCAN_TIMEOUT: Final = 30.0  # seconds
