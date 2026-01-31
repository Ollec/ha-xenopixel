"""Tests for the Xenopixel BLE protocol."""

from __future__ import annotations

import json

from custom_components.xenopixel.xenopixel_ble.protocol import (
    XenopixelProtocol,
    XenopixelState,
)


class TestXenopixelState:
    """Tests for XenopixelState dataclass."""

    def test_default_state(self) -> None:
        """Test default state values."""
        state = XenopixelState()
        assert state.is_on is False
        assert state.power_level == 0
        assert state.red == 255
        assert state.green == 255
        assert state.blue == 255
        assert state.brightness == 100
        assert state.volume == 0
        assert state.sound_font == 0
        assert state.total_sound_fonts == 0
        assert state.light_effect == 0
        assert state.hardware_version == ""
        assert state.software_version == ""

    def test_custom_state(self) -> None:
        """Test custom state values."""
        state = XenopixelState(
            is_on=True,
            power_level=22,
            red=128,
            green=64,
            blue=32,
            brightness=80,
            volume=50,
            sound_font=3,
            total_sound_fonts=10,
            light_effect=2,
            hardware_version="1.0",
            software_version="3.2.1",
        )
        assert state.is_on is True
        assert state.power_level == 22
        assert state.red == 128
        assert state.green == 64
        assert state.blue == 32
        assert state.brightness == 80
        assert state.volume == 50
        assert state.sound_font == 3
        assert state.total_sound_fonts == 10
        assert state.light_effect == 2
        assert state.hardware_version == "1.0"
        assert state.software_version == "3.2.1"


class TestXenopixelProtocol:
    """Tests for XenopixelProtocol encoder/decoder."""

    def test_encode_handshake(self) -> None:
        """Test handshake command encoding."""
        packet = XenopixelProtocol.encode_handshake()

        assert isinstance(packet, bytes)
        assert packet == b'[2,{"HandShake":"HelloDamien"}]'
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[0] == 2
        assert decoded[1]["HandShake"] == "HelloDamien"

    def test_encode_authorize(self) -> None:
        """Test authorize command encoding."""
        packet = XenopixelProtocol.encode_authorize()

        assert isinstance(packet, bytes)
        assert packet == b'[2,{"Authorize":"SaberOfDamien"}]'
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[0] == 2
        assert decoded[1]["Authorize"] == "SaberOfDamien"

    def test_decode_authorize_response(self) -> None:
        """Test decoding the authorization response from the saber."""
        data = b'[3,{"Authorize":"AccessAllowed"}]'
        result = XenopixelProtocol.decode_response(data)

        assert result is not None
        assert result["type"] == 3
        assert result["params"]["Authorize"] == "AccessAllowed"

    def test_encode_power_on(self) -> None:
        """Test power on command encoding."""
        packet = XenopixelProtocol.encode_power_on()

        assert isinstance(packet, bytes)
        decoded = json.loads(packet.decode("utf-8"))
        assert isinstance(decoded, list)
        assert len(decoded) == 2
        assert decoded[0] == 2
        assert decoded[1]["PowerOn"] is True

    def test_encode_power_off(self) -> None:
        """Test power off command encoding."""
        packet = XenopixelProtocol.encode_power_off()

        assert isinstance(packet, bytes)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[0] == 2
        assert decoded[1]["PowerOn"] is False

    def test_encode_color(self) -> None:
        """Test color command encoding."""
        packet = XenopixelProtocol.encode_color(255, 128, 64)

        assert isinstance(packet, bytes)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[0] == 2
        assert decoded[1]["BackgroundColor"] == [255, 128, 64]

    def test_encode_color_clamps_values(self) -> None:
        """Test that color values are clamped to valid range."""
        packet = XenopixelProtocol.encode_color(300, 256, 999)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[1]["BackgroundColor"] == [255, 255, 255]

        packet = XenopixelProtocol.encode_color(-10, -1, -100)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[1]["BackgroundColor"] == [0, 0, 0]

    def test_encode_brightness(self) -> None:
        """Test brightness command encoding."""
        packet = XenopixelProtocol.encode_brightness(80)

        assert isinstance(packet, bytes)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[0] == 2
        assert decoded[1]["Brightness"] == 80

    def test_encode_brightness_clamps_values(self) -> None:
        """Test that brightness values are clamped to valid range (0-100)."""
        packet = XenopixelProtocol.encode_brightness(150)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[1]["Brightness"] == 100

        packet = XenopixelProtocol.encode_brightness(-10)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[1]["Brightness"] == 0

    def test_encode_volume(self) -> None:
        """Test volume command encoding."""
        packet = XenopixelProtocol.encode_volume(50)

        assert isinstance(packet, bytes)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[0] == 2
        assert decoded[1]["Volume"] == 50

    def test_encode_volume_clamps_values(self) -> None:
        """Test that volume values are clamped to valid range (0-100)."""
        packet = XenopixelProtocol.encode_volume(150)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[1]["Volume"] == 100

        packet = XenopixelProtocol.encode_volume(-10)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[1]["Volume"] == 0

    def test_encode_sound_font(self) -> None:
        """Test sound font selection command encoding."""
        packet = XenopixelProtocol.encode_sound_font(3)

        assert isinstance(packet, bytes)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[0] == 2
        assert decoded[1]["CurrentSoundPackageNo"] == 3

    def test_encode_light_effect(self) -> None:
        """Test light effect selection command encoding."""
        packet = XenopixelProtocol.encode_light_effect(5)

        assert isinstance(packet, bytes)
        decoded = json.loads(packet.decode("utf-8"))
        assert decoded[0] == 2
        assert decoded[1]["CurrentLightEffect"] == 5

    def test_decode_response_valid(self) -> None:
        """Test decoding a valid JSON response."""
        data = b'[3,{"Power":22}]'
        result = XenopixelProtocol.decode_response(data)

        assert result is not None
        assert result["type"] == 3
        assert result["params"]["Power"] == 22

    def test_decode_response_invalid_json(self) -> None:
        """Test that invalid JSON returns None."""
        result = XenopixelProtocol.decode_response(b"not valid json")
        assert result is None

    def test_decode_response_invalid_format(self) -> None:
        """Test that non-array JSON returns None."""
        result = XenopixelProtocol.decode_response(b'{"Power": 22}')
        assert result is None

    def test_decode_response_short_array(self) -> None:
        """Test that arrays with less than 2 elements return None."""
        result = XenopixelProtocol.decode_response(b"[3]")
        assert result is None

    def test_decode_response_invalid_encoding(self) -> None:
        """Test that invalid UTF-8 returns None."""
        result = XenopixelProtocol.decode_response(b"\xff\xfe\x00\x01")
        assert result is None

    def test_parse_state_with_power_on(self) -> None:
        """Test parsing state from power on response."""
        response = {"type": 3, "params": {"PowerOn": True}}
        state = XenopixelProtocol.parse_state(response)

        assert state is not None
        assert state.is_on is True

    def test_parse_state_power_off(self) -> None:
        """Test parsing state when power is off."""
        response = {"type": 3, "params": {"PowerOn": False}}
        state = XenopixelProtocol.parse_state(response)

        assert state is not None
        assert state.is_on is False

    def test_parse_state_with_battery_level(self) -> None:
        """Test parsing battery level from Power parameter."""
        response = {"type": 3, "params": {"Power": 63}}
        state = XenopixelProtocol.parse_state(response)

        assert state is not None
        assert state.power_level == 63

    def test_parse_state_with_colors(self) -> None:
        """Test parsing state with BackgroundColor array."""
        response = {"type": 3, "params": {"BackgroundColor": [255, 128, 64]}}
        state = XenopixelProtocol.parse_state(response)

        assert state is not None
        assert state.red == 255
        assert state.green == 128
        assert state.blue == 64

    def test_parse_state_full_status(self) -> None:
        """Test parsing a full device status notification with all fields."""
        response = {
            "type": 3,
            "params": {
                "HardwareVersion": "1.0",
                "SoftwareVersion": "3.2.1",
                "Power": 63,
                "PowerOn": False,
                "CurrentSoundPackageNo": 1,
                "TotalSoundPackage": 10,
                "CurrentLightEffect": 0,
                "BackgroundColor": [255, 153, 18],
                "Brightness": 100,
                "Volume": 50,
            },
        }
        state = XenopixelProtocol.parse_state(response)

        assert state is not None
        assert state.hardware_version == "1.0"
        assert state.software_version == "3.2.1"
        assert state.power_level == 63
        assert state.is_on is False
        assert state.sound_font == 1
        assert state.total_sound_fonts == 10
        assert state.light_effect == 0
        assert state.red == 255
        assert state.green == 153
        assert state.blue == 18
        assert state.brightness == 100
        assert state.volume == 50

    def test_parse_state_none_response(self) -> None:
        """Test that None response returns None."""
        state = XenopixelProtocol.parse_state(None)  # type: ignore[arg-type]
        assert state is None

    def test_parse_state_with_volume(self) -> None:
        """Test parsing volume from status notification."""
        response = {"type": 3, "params": {"Volume": 75}}
        state = XenopixelProtocol.parse_state(response)

        assert state is not None
        assert state.volume == 75

    def test_parse_state_with_sound_font(self) -> None:
        """Test parsing sound font from status notification."""
        response = {
            "type": 3,
            "params": {"CurrentSoundPackageNo": 5, "TotalSoundPackage": 10},
        }
        state = XenopixelProtocol.parse_state(response)

        assert state is not None
        assert state.sound_font == 5
        assert state.total_sound_fonts == 10

    def test_parse_state_with_light_effect(self) -> None:
        """Test parsing light effect from status notification."""
        response = {"type": 3, "params": {"CurrentLightEffect": 3}}
        state = XenopixelProtocol.parse_state(response)

        assert state is not None
        assert state.light_effect == 3

    def test_parse_state_with_versions(self) -> None:
        """Test parsing hardware and software versions."""
        response = {
            "type": 3,
            "params": {"HardwareVersion": "2.0", "SoftwareVersion": "4.0.0"},
        }
        state = XenopixelProtocol.parse_state(response)

        assert state is not None
        assert state.hardware_version == "2.0"
        assert state.software_version == "4.0.0"
