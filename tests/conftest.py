"""Fixtures for Xenopixel tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_bleak_client() -> Generator[MagicMock]:
    """Mock BleakClient for testing without actual Bluetooth hardware."""
    with patch("bleak.BleakClient") as mock_client:
        client_instance = MagicMock()
        client_instance.is_connected = True
        client_instance.connect = MagicMock(return_value=True)
        client_instance.disconnect = MagicMock(return_value=True)
        client_instance.write_gatt_char = MagicMock(return_value=None)
        mock_client.return_value.__aenter__.return_value = client_instance
        yield mock_client


@pytest.fixture
def mock_bluetooth_service_info() -> MagicMock:
    """Create a mock BluetoothServiceInfoBleak."""
    service_info = MagicMock()
    service_info.address = "AA:BB:CC:DD:EE:FF"
    service_info.name = "Xeno_Saber_01"
    service_info.service_uuids = ["0000dae0-0000-1000-8000-00805f9b34fb"]
    service_info.manufacturer_data = {}
    service_info.service_data = {}
    return service_info
