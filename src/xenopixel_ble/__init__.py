"""Xenopixel BLE protocol library."""

from __future__ import annotations

from .const import (
    CHAR_CONTROL_ALT_UUID,
    CHAR_CONTROL_UUID,
    DOMAIN,
    SERVICE_UUID,
    SERVICE_UUID_ALT,
)
from .protocol import XenopixelProtocol

__all__ = [
    "CHAR_CONTROL_ALT_UUID",
    "CHAR_CONTROL_UUID",
    "DOMAIN",
    "SERVICE_UUID",
    "SERVICE_UUID_ALT",
    "XenopixelProtocol",
]
