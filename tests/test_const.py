"""Tests for the Xenopixel constants."""

from __future__ import annotations

from custom_components.xenopixel.const import (
    CHAR_CONTROL_ALT_UUID,
    CHAR_CONTROL_UUID,
    DOMAIN,
    SERVICE_UUID,
    SERVICE_UUID_ALT,
)
from custom_components.xenopixel.xenopixel_ble.const import (
    AUTHORIZE_RESPONSE,
    AUTHORIZE_VALUE,
    HANDSHAKE_VALUE,
    MSG_TYPE_COMMAND,
    MSG_TYPE_STATUS,
    PARAM_AUTHORIZE,
    PARAM_HANDSHAKE,
)


def test_domain() -> None:
    """Test that domain is correctly defined."""
    assert DOMAIN == "xenopixel"


def test_service_uuid_format() -> None:
    """Test that primary service UUID is in correct format (0xDAE0)."""
    assert len(SERVICE_UUID) == 36
    assert SERVICE_UUID.count("-") == 4
    assert SERVICE_UUID == "0000dae0-0000-1000-8000-00805f9b34fb"


def test_service_uuid_alt_format() -> None:
    """Test that secondary service UUID is in correct format (0x3AB0)."""
    assert len(SERVICE_UUID_ALT) == 36
    assert SERVICE_UUID_ALT.count("-") == 4
    assert SERVICE_UUID_ALT == "00003ab0-0000-1000-8000-00805f9b34fb"


def test_control_characteristic_uuid_format() -> None:
    """Test that control characteristic UUID is in correct format (0xDAE1)."""
    assert len(CHAR_CONTROL_UUID) == 36
    assert CHAR_CONTROL_UUID.count("-") == 4
    assert CHAR_CONTROL_UUID == "0000dae1-0000-1000-8000-00805f9b34fb"


def test_control_alt_characteristic_uuid_format() -> None:
    """Test that alt control characteristic UUID is in correct format (0x3AB1)."""
    assert len(CHAR_CONTROL_ALT_UUID) == 36
    assert CHAR_CONTROL_ALT_UUID.count("-") == 4
    assert CHAR_CONTROL_ALT_UUID == "00003ab1-0000-1000-8000-00805f9b34fb"


def test_message_types() -> None:
    """Test message type constants."""
    assert MSG_TYPE_COMMAND == 2
    assert MSG_TYPE_STATUS == 3


def test_handshake_value() -> None:
    """Test handshake authorization value."""
    assert HANDSHAKE_VALUE == "HelloDamien"
    assert PARAM_HANDSHAKE == "HandShake"


def test_authorize_value() -> None:
    """Test authorize authorization value."""
    assert AUTHORIZE_VALUE == "SaberOfDamien"
    assert PARAM_AUTHORIZE == "Authorize"


def test_authorize_response() -> None:
    """Test expected authorization response."""
    assert AUTHORIZE_RESPONSE == "AccessAllowed"
