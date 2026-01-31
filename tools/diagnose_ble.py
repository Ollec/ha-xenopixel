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
import subprocess

from bleak import BleakClient

KNOWN_MAC = "B0:CB:D8:DB:E1:AE"


def run_cmd(cmd: str) -> str:
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"Error: {e}"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


async def diagnose() -> None:
    """Run diagnostics."""
    print("BLE Environment Diagnostics for Xenopixel Saber")
    print("=" * 60)

    # System info
    print_section("System Information")
    print(f"OS: {run_cmd('uname -a')}")
    print(f"Kernel: {run_cmd('uname -r')}")

    # BlueZ version
    print_section("BlueZ Information")
    print(
        f"bluetoothd version: {run_cmd('bluetoothd --version 2>/dev/null || bluetoothctl --version')}"
    )
    print(
        f"BlueZ packages: {run_cmd('dpkg -l 2>/dev/null | grep -i bluez | head -5 || pacman -Q bluez 2>/dev/null || rpm -qa bluez 2>/dev/null')}"
    )

    # Bluetooth service status
    print_section("Bluetooth Service")
    print(
        f"Service status: {run_cmd('systemctl status bluetooth --no-pager -l 2>/dev/null | head -20')}"
    )

    # Adapter info
    print_section("Bluetooth Adapter")
    print(
        f"hciconfig: {run_cmd('hciconfig -a 2>/dev/null || echo hciconfig not found')}"
    )
    print(
        f"\nbtmgmt info: {run_cmd('btmgmt info 2>/dev/null | head -30 || echo btmgmt not found/needs sudo')}"
    )

    # Known device pairing state
    print_section(f"Device Pairing State ({KNOWN_MAC})")
    print(
        f"bluetoothctl info:\n{run_cmd(f'echo "info {KNOWN_MAC}" | bluetoothctl 2>/dev/null | grep -E "(Device|Name|Paired|Bonded|Trusted|Connected|UUID)"')}"
    )

    # Try to connect and inspect GATT
    print_section("GATT Inspection")
    try:
        print(f"Connecting to {KNOWN_MAC}...")
        async with BleakClient(KNOWN_MAC, timeout=15.0) as client:
            print(f"Connected: {client.is_connected}")
            print(f"MTU: {client.mtu_size}")

            # Get bleak backend info
            print(f"\nBackend type: {type(client).__name__}")

            # Inspect services
            print("\nGATT Services of interest:")
            for service in client.services:
                if "dae" in service.uuid.lower() or "3ab" in service.uuid.lower():
                    print(f"\n  Service: {service.uuid}")
                    for char in service.characteristics:
                        print(f"    Characteristic: {char.uuid}")
                        print(f"      Handle: {char.handle}")
                        print(f"      Properties: {char.properties}")

                        # Try to read the characteristic
                        if "read" in char.properties:
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                print(f"      Current value: {value}")
                                try:
                                    print(f"      Decoded: {value.decode('utf-8')}")
                                except:
                                    pass
                            except Exception as e:
                                print(f"      Read error: {e}")

                        # Check descriptors
                        for desc in char.descriptors:
                            print(
                                f"      Descriptor: {desc.uuid} (handle {desc.handle})"
                            )
                            if "2902" in str(desc.uuid):
                                # Try to read CCCD
                                try:
                                    cccd_val = await client.read_gatt_descriptor(
                                        desc.handle
                                    )
                                    print(
                                        f"        CCCD value: {cccd_val.hex()} (0100=notify enabled)"
                                    )
                                except Exception as e:
                                    print(f"        CCCD read error: {e}")

            # Try to enable notifications and capture exact error
            print("\n" + "-" * 40)
            print("Testing notification enable...")

            for char_uuid, name in [
                (CHAR_CONTROL_ALT_UUID, "0x3AB1"),
                (CHAR_CONTROL_UUID, "0xDAE1"),
            ]:
                print(f"\n  {name} ({char_uuid[:8]}...):")
                try:
                    await client.start_notify(char_uuid, lambda s, d: None)
                    print("    ✅ start_notify succeeded")
                    await client.stop_notify(char_uuid)
                except Exception as e:
                    print(f"    ❌ {type(e).__name__}: {e}")

    except Exception as e:
        print(f"Connection failed: {e}")

    # Check D-Bus BlueZ object for device
    print_section("D-Bus Device Properties")
    dbus_path = f"/org/bluez/hci0/dev_{KNOWN_MAC.replace(':', '_')}"
    print(f"D-Bus path: {dbus_path}")
    print(
        f"Properties: {run_cmd(f'busctl introspect org.bluez {dbus_path} 2>/dev/null | head -30 || echo busctl not found')}"
    )

    # Summary and recommendations
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


# UUIDs
CHAR_CONTROL_UUID = "0000dae1-0000-1000-8000-00805f9b34fb"
CHAR_CONTROL_ALT_UUID = "00003ab1-0000-1000-8000-00805f9b34fb"


if __name__ == "__main__":
    asyncio.run(diagnose())
