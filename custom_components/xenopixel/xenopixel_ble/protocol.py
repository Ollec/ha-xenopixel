"""Xenopixel BLE protocol implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .const import (
    AUTHORIZE_VALUE,
    HANDSHAKE_VALUE,
    LIGHT_EFFECT_MAX,
    LIGHT_EFFECT_MIN,
    MSG_TYPE_COMMAND,
    PARAM_AUTHORIZE,
    PARAM_BACKGROUND_COLOR,
    PARAM_BRIGHTNESS,
    PARAM_CURRENT_LIGHT_EFFECT,
    PARAM_CURRENT_SOUND_PACKAGE,
    PARAM_HANDSHAKE,
    PARAM_HARDWARE_VERSION,
    PARAM_POWER,
    PARAM_POWER_ON,
    PARAM_SOFTWARE_VERSION,
    PARAM_TOTAL_SOUND_PACKAGES,
    PARAM_VOLUME,
)


@dataclass
class XenopixelState:
    """Represents the current state of a Xenopixel lightsaber."""

    is_on: bool = False
    power_level: int = 0
    red: int = 255
    green: int = 255
    blue: int = 255
    brightness: int = 100
    volume: int = 0
    sound_font: int = 0
    total_sound_fonts: int = 0
    light_effect: int = 0
    hardware_version: str = ""
    software_version: str = ""


class XenopixelProtocol:
    """Protocol encoder/decoder for Xenopixel BLE communication.

    This class handles the encoding of commands and decoding of responses
    for the Xenopixel V3 JSON-based BLE protocol.

    Protocol Details (confirmed via HCI snoop capture 2026-01-28, 2026-01-30):
    - Commands: sent TO device on 0x3AB1, message type 2
    - HandShake: sent TO device on 0xDAE1, message type 2
    - Notifications: received FROM device on 0xDAE1, message type 3
    - Message format: JSON array [type, {parameters}]

    Authorization flow (must complete before commands are accepted):
    1. Enable indications on 0x2A05 (CCCD write)
    2. Send [2,{"HandShake":"HelloDamien"}] to 0xDAE1
    3. Send [2,{"Authorize":"SaberOfDamien"}] to 0x3AB1
    4. Receive [3,{"Authorize":"AccessAllowed"}] on 0x3AB1
    """

    @staticmethod
    def encode_handshake() -> bytes:
        """Encode the handshake message (sent to 0xDAE1).

        This must be sent before the authorize message.
        Uses ATT Write Request (with response) to 0xDAE1.

        Returns:
            bytes: [2,{"HandShake":"HelloDamien"}] as UTF-8 bytes.
        """
        message = [MSG_TYPE_COMMAND, {PARAM_HANDSHAKE: HANDSHAKE_VALUE}]
        return json.dumps(message, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def encode_authorize() -> bytes:
        """Encode the authorization message (sent to 0x3AB1).

        This must be sent after the handshake message.
        Uses ATT Write Command (no response) to 0x3AB1.

        Returns:
            bytes: [2,{"Authorize":"SaberOfDamien"}] as UTF-8 bytes.
        """
        message = [MSG_TYPE_COMMAND, {PARAM_AUTHORIZE: AUTHORIZE_VALUE}]
        return json.dumps(message, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def encode_power_on() -> bytes:
        """Encode a power on command (ignite blade).

        Returns:
            bytes: The encoded JSON command as UTF-8 bytes.

        Protocol confirmed via HCI snoop capture 2026-01-28:
        Command: [2,{"PowerOn":true}] sent to 0x3AB1
        """
        message = [MSG_TYPE_COMMAND, {PARAM_POWER_ON: True}]
        return json.dumps(message, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def encode_power_off() -> bytes:
        """Encode a power off command (retract blade).

        Returns:
            bytes: The encoded JSON command as UTF-8 bytes.

        Protocol confirmed via HCI snoop capture 2026-01-28:
        Command: [2,{"PowerOn":false}] sent to 0x3AB1
        """
        message = [MSG_TYPE_COMMAND, {PARAM_POWER_ON: False}]
        return json.dumps(message, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def encode_color(red: int, green: int, blue: int) -> bytes:
        """Encode a color change command.

        Args:
            red: Red component (0-255).
            green: Green component (0-255).
            blue: Blue component (0-255).

        Returns:
            bytes: The encoded JSON command as UTF-8 bytes.

        Protocol confirmed via HCI snoop capture 2026-01-28:
        Command: [2,{"BackgroundColor":[R,G,B]}] sent to 0x3AB1
        """
        # Clamp values to valid range
        red = max(0, min(255, red))
        green = max(0, min(255, green))
        blue = max(0, min(255, blue))

        message = [MSG_TYPE_COMMAND, {PARAM_BACKGROUND_COLOR: [red, green, blue]}]
        return json.dumps(message, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def encode_brightness(brightness: int) -> bytes:
        """Encode a brightness change command.

        Args:
            brightness: Brightness level (0-100).

        Returns:
            bytes: The encoded JSON command as UTF-8 bytes.

        Protocol: [2,{"Brightness":value}] sent to 0x3AB1
        """
        brightness = max(0, min(100, brightness))

        message = [MSG_TYPE_COMMAND, {PARAM_BRIGHTNESS: brightness}]
        return json.dumps(message, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def encode_volume(volume: int) -> bytes:
        """Encode a volume change command.

        Args:
            volume: Volume level (0-100).

        Returns:
            bytes: The encoded JSON command as UTF-8 bytes.

        Protocol: [2,{"Volume":value}] sent to 0x3AB1
        """
        volume = max(0, min(100, volume))

        message = [MSG_TYPE_COMMAND, {PARAM_VOLUME: volume}]
        return json.dumps(message, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def encode_sound_font(font_no: int) -> bytes:
        """Encode a sound font selection command.

        Args:
            font_no: Sound font number.

        Returns:
            bytes: The encoded JSON command as UTF-8 bytes.

        Protocol: [2,{"CurrentSoundPackageNo":value}] sent to 0x3AB1
        """
        message = [MSG_TYPE_COMMAND, {PARAM_CURRENT_SOUND_PACKAGE: font_no}]
        return json.dumps(message, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def encode_light_effect(effect: int) -> bytes:
        """Encode a light effect selection command.

        Args:
            effect: Light effect number (1-9).

        Returns:
            bytes: The encoded JSON command as UTF-8 bytes.

        Protocol: [2,{"CurrentLightEffect":value}] sent to 0x3AB1
        """
        effect = max(LIGHT_EFFECT_MIN, min(LIGHT_EFFECT_MAX, effect))

        message = [MSG_TYPE_COMMAND, {PARAM_CURRENT_LIGHT_EFFECT: effect}]
        return json.dumps(message, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def decode_response(data: bytes) -> dict[str, Any] | None:
        """Decode a response packet from the device.

        Args:
            data: Raw bytes received from the device (UTF-8 JSON).

        Returns:
            Decoded response as a dictionary with 'type' and 'params' keys,
            or None if invalid.
        """
        try:
            text = data.decode("utf-8")
            parsed = json.loads(text)

            if not isinstance(parsed, list) or len(parsed) < 2:
                return None

            msg_type = parsed[0]
            params = parsed[1] if isinstance(parsed[1], dict) else {}

            return {"type": msg_type, "params": params}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    # Mapping from BLE parameter names to XenopixelState field names
    _PARAM_TO_FIELD: dict[str, str] = {
        PARAM_POWER_ON: "is_on",
        PARAM_POWER: "power_level",
        PARAM_BRIGHTNESS: "brightness",
        PARAM_VOLUME: "volume",
        PARAM_CURRENT_SOUND_PACKAGE: "sound_font",
        PARAM_TOTAL_SOUND_PACKAGES: "total_sound_fonts",
        PARAM_CURRENT_LIGHT_EFFECT: "light_effect",
        PARAM_HARDWARE_VERSION: "hardware_version",
        PARAM_SOFTWARE_VERSION: "software_version",
    }

    @staticmethod
    def _apply_color(state: XenopixelState, color: Any) -> None:
        """Apply BackgroundColor [R, G, B] array to state."""
        if isinstance(color, list) and len(color) >= 3:
            state.red = color[0]
            state.green = color[1]
            state.blue = color[2]

    @staticmethod
    def parse_state(response: dict[str, Any]) -> XenopixelState | None:
        """Parse a response into a XenopixelState object.

        Args:
            response: Decoded response from decode_response().

        Returns:
            XenopixelState object, or None if response is invalid.

        Protocol notes (from nRF Logger capture 2026-01-28):
        - PowerOn: boolean (true = blade on, false = blade off)
        - Power: int (battery percentage, e.g., 63 = 63%)
        - BackgroundColor: [R, G, B] array
        - Brightness: int
        """
        if response is None:
            return None

        params = response.get("params", {})
        state = XenopixelState()

        # Apply simple 1:1 parameter-to-field mappings
        for param_name, field_name in XenopixelProtocol._PARAM_TO_FIELD.items():
            if param_name in params:
                setattr(state, field_name, params[param_name])

        # BackgroundColor needs special handling ([R, G, B] array)
        if PARAM_BACKGROUND_COLOR in params:
            XenopixelProtocol._apply_color(state, params[PARAM_BACKGROUND_COLOR])

        return state
