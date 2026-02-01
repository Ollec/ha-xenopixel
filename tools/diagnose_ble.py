#!/usr/bin/env python3
"""Diagnose BLE environment and device security requirements.

This script gathers information about:
- BlueZ version
- Kernel Bluetooth modules
- Device bonding state
- GATT characteristic permissions

Usage:
    uv run python tools/diagnose_ble.py
"""

from __future__ import annotations

import asyncio
import subprocess  # noqa: S404 — used with fixed argument lists only

from bleak import BleakClient

KNOWN_MAC = "B0:CB:D8:DB:E1:AE"

# UUIDs
CHAR_CONTROL_UUID = "0000dae1-0000-1000-8000-00805f9b34fb"
CHAR_CONTROL_ALT_UUID = "00003ab1-0000-1000-8000-00805f9b34fb"


def run_cmd(args: list[str]) -> str:
    """Run command with fixed argument list and return output."""
    try:
        result = subprocess.run(  # noqa: S603
            args, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"Error: {e}"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def diagnose_system_info() -> None:
    """Print system and BlueZ information."""
    print_section("System Information")
    print(f"OS: {run_cmd(['uname', '-a'])}")
    print(f"Kernel: {run_cmd(['uname', '-r'])}")

    print_section("BlueZ Information")
    print(f"bluetoothd version: {run_cmd(['bluetoothd', '--version'])}")
    print(f"BlueZ packages: {run_cmd(['dpkg', '-l'])}")

    print_section("Bluetooth Service")
    print(
        f"Service status: {run_cmd(['systemctl', 'status', 'bluetooth', '--no-pager', '-l'])}"
    )


def diagnose_adapter_info() -> None:
    """Print Bluetooth adapter information."""
    print_section("Bluetooth Adapter")
    print(f"hciconfig: {run_cmd(['hciconfig', '-a'])}")
    print(f"\nbtmgmt info: {run_cmd(['btmgmt', 'info'])}")


def diagnose_pairing_state() -> None:
    """Print known device pairing state."""
    mac = KNOWN_MAC
    print_section(f"Device Pairing State ({mac})")
    print(f"bluetoothctl info:\n{run_cmd(['bluetoothctl', 'info', mac])}")


async def diagnose_gatt() -> None:
    """Connect and inspect GATT services."""
    print_section("GATT Inspection")
    try:
        print(f"Connecting to {KNOWN_MAC}...")
        async with BleakClient(KNOWN_MAC, timeout=15.0) as client:
            print(f"Connected: {client.is_connected}")
            print(f"MTU: {client.mtu_size}")
            print(f"\nBackend type: {type(client).__name__}")

            await _inspect_services(client)
            await _test_notifications(client)

    except Exception as e:
        print(f"Connection failed: {e}")


async def _inspect_services(client: BleakClient) -> None:
    """Inspect GATT services of interest."""
    print("\nGATT Services of interest:")
    for service in client.services:
        if "dae" not in service.uuid.lower() and "3ab" not in service.uuid.lower():
            continue
        print(f"\n  Service: {service.uuid}")
        for char in service.characteristics:
            print(f"    Characteristic: {char.uuid}")
            print(f"      Handle: {char.handle}")
            print(f"      Properties: {char.properties}")

            if "read" in char.properties:
                await _try_read_char(client, char)

            for desc in char.descriptors:
                print(f"      Descriptor: {desc.uuid} (handle {desc.handle})")
                if "2902" in str(desc.uuid):
                    await _try_read_cccd(client, desc)


async def _try_read_char(client: BleakClient, char: object) -> None:
    """Try to read a characteristic value."""
    try:
        value = await client.read_gatt_char(char.uuid)
        print(f"      Current value: {value}")
        try:
            print(f"      Decoded: {value.decode('utf-8')}")
        except UnicodeDecodeError:
            pass
    except Exception as e:
        print(f"      Read error: {e}")


async def _try_read_cccd(client: BleakClient, desc: object) -> None:
    """Try to read a CCCD descriptor value."""
    try:
        cccd_val = await client.read_gatt_descriptor(desc.handle)
        print(f"        CCCD value: {cccd_val.hex()} (0100=notify enabled)")
    except Exception as e:
        print(f"        CCCD read error: {e}")


async def _test_notifications(client: BleakClient) -> None:
    """Test enabling notifications on known characteristics."""
    print("\n" + "-" * 40)
    print("Testing notification enable...")

    for char_uuid, name in [
        (CHAR_CONTROL_ALT_UUID, "0x3AB1"),
        (CHAR_CONTROL_UUID, "0xDAE1"),
    ]:
        print(f"\n  {name} ({char_uuid[:8]}...):")
        try:
            await client.start_notify(char_uuid, lambda s, d: None)
            print("    start_notify succeeded")
            await client.stop_notify(char_uuid)
        except Exception as e:
            print(f"    {type(e).__name__}: {e}")


def diagnose_dbus() -> None:
    """Check D-Bus BlueZ object for device."""
    print_section("D-Bus Device Properties")
    dbus_path = f"/org/bluez/hci0/dev_{KNOWN_MAC.replace(':', '_')}"
    print(f"D-Bus path: {dbus_path}")
    print(f"Properties: {run_cmd(['busctl', 'introspect', 'org.bluez', dbus_path])}")


def print_recommendations() -> None:
    """Print summary and recommendations."""
    print_section("Summary & Recommendations")
    print("""
The 'NotPermitted' error on CCCD writes typically means:

1. The device requires ENCRYPTED writes to CCCD
   - BLE devices can specify security requirements per characteristic
   - This device likely requires authentication/encryption for CCCD

2. BlueZ handling varies by version
   - Some versions auto-pair, others don't
   - The 'sc' (Secure Connections) setting matters

RECOMMENDATIONS:

A) Try pairing first, then connecting:
   bluetoothctl
   > scan on
   > pair B0:CB:D8:DB:E1:AE  (wait for pairing)
   > trust B0:CB:D8:DB:E1:AE
   > connect B0:CB:D8:DB:E1:AE
   > quit

   Then run: uv run python tools/test_saber.py blind

B) Try with sudo to allow btmgmt config:
   sudo uv run python tools/test_secure_pair.py

C) Check if device appears as bonded after Android connection:
   - Pair with Android phone first
   - Check if bond info helps Linux

D) ESP32 Proxy (most reliable):
   - Use ESP32 with ESPHome as BLE-to-MQTT bridge
   - ESP32's BLE stack handles this device properly
""")


async def diagnose() -> None:
    """Run diagnostics."""
    print("BLE Environment Diagnostics for Xenopixel Saber")
    print("=" * 60)

    diagnose_system_info()
    diagnose_adapter_info()
    diagnose_pairing_state()
    await diagnose_gatt()
    diagnose_dbus()
    print_recommendations()


if __name__ == "__main__":
    asyncio.run(diagnose())
