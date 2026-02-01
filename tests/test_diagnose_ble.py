"""Tests for tools/diagnose_ble.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.diagnose_ble import (
    _inspect_services,
    _test_notifications,
    _try_read_cccd,
    _try_read_char,
    diagnose_adapter_info,
    diagnose_dbus,
    diagnose_pairing_state,
    diagnose_system_info,
    print_recommendations,
    print_section,
    run_cmd,
)

# --- run_cmd ---


def test_run_cmd_success():
    """Successful command returns stdout."""
    result = run_cmd(["echo", "hello"])
    assert result == "hello"


def test_run_cmd_failure():
    """Failed command returns stderr or error message."""
    result = run_cmd(["false"])
    # 'false' exits non-zero but produces no output
    assert isinstance(result, str)


def test_run_cmd_nonexistent():
    """Non-existent command returns error string."""
    result = run_cmd(["/nonexistent/binary"])
    assert result.startswith("Error:")


def test_run_cmd_timeout():
    """Command timeout returns error string."""
    with patch(
        "tools.diagnose_ble.subprocess.run", side_effect=TimeoutError("timed out")
    ):
        result = run_cmd(["sleep", "999"])
    assert "Error:" in result


# --- print_section ---


def test_print_section(capsys):
    """Section header is formatted correctly."""
    print_section("Test Title")
    output = capsys.readouterr().out
    assert "Test Title" in output
    assert "=" * 60 in output


# --- diagnose functions (system commands) ---


@patch("tools.diagnose_ble.run_cmd", return_value="mocked output")
def test_diagnose_system_info(mock_cmd, capsys):
    """System info calls run_cmd and prints output."""
    diagnose_system_info()
    output = capsys.readouterr().out
    assert "System Information" in output
    assert "mocked output" in output
    assert mock_cmd.call_count >= 4


@patch("tools.diagnose_ble.run_cmd", return_value="mocked output")
def test_diagnose_adapter_info(mock_cmd, capsys):
    """Adapter info calls run_cmd."""
    diagnose_adapter_info()
    output = capsys.readouterr().out
    assert "Bluetooth Adapter" in output
    assert mock_cmd.call_count >= 2


@patch("tools.diagnose_ble.run_cmd", return_value="mocked output")
def test_diagnose_pairing_state(mock_cmd, capsys):
    """Pairing state calls bluetoothctl."""
    diagnose_pairing_state()
    output = capsys.readouterr().out
    assert "Device Pairing State" in output


@patch("tools.diagnose_ble.run_cmd", return_value="mocked output")
def test_diagnose_dbus(mock_cmd, capsys):
    """D-Bus diagnostics prints device path."""
    diagnose_dbus()
    output = capsys.readouterr().out
    assert "D-Bus Device Properties" in output
    assert "org/bluez" in output


# --- print_recommendations ---


def test_print_recommendations(capsys):
    """Recommendations section prints expected content."""
    print_recommendations()
    output = capsys.readouterr().out
    assert "RECOMMENDATIONS" in output
    assert "ESP32 Proxy" in output


# --- async GATT helpers ---


@pytest.mark.asyncio
async def test_try_read_char_success(capsys):
    """Successful characteristic read prints value."""
    client = AsyncMock()
    client.read_gatt_char.return_value = b"test_value"

    char = MagicMock()
    char.uuid = "0000dae1-0000-1000-8000-00805f9b34fb"

    await _try_read_char(client, char)
    output = capsys.readouterr().out
    assert "test_value" in output


@pytest.mark.asyncio
async def test_try_read_char_non_utf8(capsys):
    """Non-UTF-8 value is printed as bytes only."""
    client = AsyncMock()
    client.read_gatt_char.return_value = bytes([0xFF, 0xFE])

    char = MagicMock()
    char.uuid = "test-uuid"

    await _try_read_char(client, char)
    output = capsys.readouterr().out
    assert "Current value" in output


@pytest.mark.asyncio
async def test_try_read_char_error(capsys):
    """Read error is printed gracefully."""
    client = AsyncMock()
    client.read_gatt_char.side_effect = Exception("read failed")

    char = MagicMock()
    char.uuid = "test-uuid"

    await _try_read_char(client, char)
    output = capsys.readouterr().out
    assert "Read error" in output


@pytest.mark.asyncio
async def test_try_read_cccd_success(capsys):
    """Successful CCCD read prints hex value."""
    client = AsyncMock()
    client.read_gatt_descriptor.return_value = b"\x01\x00"

    desc = MagicMock()
    desc.handle = 42

    await _try_read_cccd(client, desc)
    output = capsys.readouterr().out
    assert "CCCD value" in output
    assert "0100" in output


@pytest.mark.asyncio
async def test_try_read_cccd_error(capsys):
    """CCCD read error is printed gracefully."""
    client = AsyncMock()
    client.read_gatt_descriptor.side_effect = Exception("cccd fail")

    desc = MagicMock()
    desc.handle = 42

    await _try_read_cccd(client, desc)
    output = capsys.readouterr().out
    assert "CCCD read error" in output


# --- _inspect_services ---


@pytest.mark.asyncio
async def test_inspect_services(capsys):
    """Services with 'dae' or '3ab' in UUID are inspected."""
    desc = MagicMock()
    desc.uuid = "00002902-0000-1000-8000-00805f9b34fb"
    desc.handle = 10

    char = MagicMock()
    char.uuid = "0000dae1-0000-1000-8000-00805f9b34fb"
    char.handle = 5
    char.properties = ["write", "notify"]
    char.descriptors = [desc]

    service = MagicMock()
    service.uuid = "0000dae0-0000-1000-8000-00805f9b34fb"
    service.characteristics = [char]

    # Also include a non-matching service to test filtering
    other_service = MagicMock()
    other_service.uuid = "00001800-0000-1000-8000-00805f9b34fb"

    client = AsyncMock()
    client.services = [service, other_service]
    client.read_gatt_descriptor.return_value = b"\x01\x00"

    await _inspect_services(client)
    output = capsys.readouterr().out
    assert "dae0" in output
    assert "dae1" in output
    # Non-matching service should not appear
    assert "1800" not in output


@pytest.mark.asyncio
async def test_inspect_services_readable_char(capsys):
    """Characteristics with 'read' property are read."""
    char = MagicMock()
    char.uuid = "0000dae1-0000-1000-8000-00805f9b34fb"
    char.handle = 5
    char.properties = ["read", "notify"]
    char.descriptors = []

    service = MagicMock()
    service.uuid = "0000dae0-0000-1000-8000-00805f9b34fb"
    service.characteristics = [char]

    client = AsyncMock()
    client.services = [service]
    client.read_gatt_char.return_value = b"data"

    await _inspect_services(client)
    client.read_gatt_char.assert_called_once()


# --- _test_notifications ---


@pytest.mark.asyncio
async def test_test_notifications_success(capsys):
    """Notification test succeeds for both characteristics."""
    client = AsyncMock()
    await _test_notifications(client)
    output = capsys.readouterr().out
    assert "start_notify succeeded" in output
    assert client.start_notify.call_count == 2
    assert client.stop_notify.call_count == 2


@pytest.mark.asyncio
async def test_test_notifications_failure(capsys):
    """Notification failure is handled gracefully."""
    client = AsyncMock()
    client.start_notify.side_effect = Exception("NotPermitted")

    await _test_notifications(client)
    output = capsys.readouterr().out
    assert "NotPermitted" in output
