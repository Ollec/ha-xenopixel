#!/usr/bin/env python3
"""Test script for Xenopixel saber BLE communication.

Usage:
    # Scan for devices
    uv run python tools/test_saber.py scan

    # Connect and read current state
    uv run python tools/test_saber.py read

    # Power on (ignite blade)
    uv run python tools/test_saber.py power on

    # Power off (retract blade)
    uv run python tools/test_saber.py power off

    # Set color (RGB)
    uv run python tools/test_saber.py color 255 0 0

    # Set brightness (0-100)
    uv run python tools/test_saber.py brightness 50

    # Send raw JSON command
    uv run python tools/test_saber.py raw '[3,{"PowerOn":true}]'

    # Send to ALT characteristic (0x3AB1)
    uv run python tools/test_saber.py alt '[3,{"PowerOn":true}]'

    # Blind mode - skip notifications, try direct writes
    uv run python tools/test_saber.py blind

Protocol format (confirmed via HCI snoop capture 2026-01-28):
    COMMANDS (type 2, to 0x3AB1 with Write Command):
    Power:      [2,{"PowerOn":true}] or [2,{"PowerOn":false}]
    Color:      [2,{"BackgroundColor":[R,G,B]}]
    Brightness: [2,{"Brightness":value}]

    NOTIFICATIONS (type 3, from 0xDAE1):
    Status:     [3,{"PowerOn":true}] etc.
"""

from __future__ import annotations

import asyncio
import sys

from bleak import BleakClient, BleakScanner

# UUIDs discovered from nRF Connect
SERVICE_UUID = "0000dae0-0000-1000-8000-00805f9b34fb"
CHAR_CONTROL_UUID = "0000dae1-0000-1000-8000-00805f9b34fb"

# Secondary service (try this for commands)
SERVICE_UUID_ALT = "00003ab0-0000-1000-8000-00805f9b34fb"
CHAR_CONTROL_ALT_UUID = "00003ab1-0000-1000-8000-00805f9b34fb"

# Known MAC address (update if different)
KNOWN_MAC = "B0:CB:D8:DB:E1:AE"


def notification_handler(sender: int, data: bytearray) -> None:
    """Handle notifications from the saber."""
    try:
        text = data.decode("utf-8")
        print(f"📨 Notification: {text}")
    except UnicodeDecodeError:
        print(f"📨 Notification (hex): {data.hex()}")


async def _dump_gatt_services(client: BleakClient) -> None:
    """Print all GATT services and their characteristics."""
    print("\n📋 GATT Services:")
    for service in client.services:
        print(f"\n  Service: {service.uuid}")
        for char in service.characteristics:
            props = ", ".join(char.properties)
            print(f"    Char: {char.uuid} [{props}]")
            for desc in char.descriptors:
                print(f"      Desc: {desc.uuid}")
                if "2902" in str(desc.uuid):
                    try:
                        value = await client.read_gatt_descriptor(desc.handle)
                        print(f"        CCCD value: {value.hex()}")
                    except Exception as e:
                        print(f"        CCCD read error: {e}")


async def _manually_enable_notifications(client: BleakClient) -> None:
    """Try to manually write to CCCD to enable notifications."""
    print("\n🔧 Manually enabling notifications...")
    for service in client.services:
        for char in service.characteristics:
            if "notify" not in char.properties:
                continue
            for desc in char.descriptors:
                if "2902" not in str(desc.uuid):
                    continue
                print(f"  Writing 0x0100 to CCCD for {char.uuid}...")
                try:
                    await client.write_gatt_descriptor(
                        desc.handle, bytearray([0x01, 0x00])
                    )
                    print("    ✅ Written")
                except Exception as e:
                    print(f"    ❌ Error: {e}")


async def debug_gatt() -> None:
    """Debug GATT structure and notification setup."""
    print(f"🔌 Connecting to {KNOWN_MAC}...")

    async with BleakClient(KNOWN_MAC) as client:
        print("🔐 Attempting to pair through bleak...")
        try:
            paired = await client.pair()
            print(f"   Pair result: {paired}")
        except Exception as e:
            print(f"   Pair error: {e}")
        print(f"✅ Connected: {client.is_connected}")
        print(f"📊 MTU: {client.mtu_size}")

        await _dump_gatt_services(client)
        await _manually_enable_notifications(client)

        print("\n📡 Starting notifications via bleak...")
        await client.start_notify(CHAR_CONTROL_UUID, notification_handler)
        await client.start_notify(CHAR_CONTROL_ALT_UUID, notification_handler)

        print("\n⏳ Waiting 15 seconds for notifications...")
        await asyncio.sleep(15)


async def scan_devices() -> None:
    """Scan for BLE devices and show Xenopixel sabers."""
    print("🔍 Scanning for BLE devices (10 seconds)...")
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)

    print(f"\nFound {len(devices)} devices:\n")

    for device, adv_data in devices.values():
        # Check if it has our service UUID
        is_saber = SERVICE_UUID.lower() in [
            str(u).lower() for u in adv_data.service_uuids
        ]
        marker = "⚔️ SABER" if is_saber else "  "

        name = device.name or "Unknown"
        print(f"{marker} {name:20} {device.address}  RSSI: {adv_data.rssi}")

        if is_saber or "saber" in name.lower():
            print(f"       Services: {adv_data.service_uuids}")


async def connect_and_read() -> None:
    """Connect to saber and read current state."""
    print(f"🔌 Connecting to {KNOWN_MAC}...")

    async with BleakClient(KNOWN_MAC) as client:
        print(f"✅ Connected: {client.is_connected}")

        # Enable notifications on BOTH characteristics
        await client.start_notify(CHAR_CONTROL_UUID, notification_handler)
        print("📡 Notifications enabled on PRIMARY (0xDAE1)")

        await client.start_notify(CHAR_CONTROL_ALT_UUID, notification_handler)
        print("📡 Notifications enabled on ALT (0x3AB1)")

        # Read current value from PRIMARY
        value = await client.read_gatt_char(CHAR_CONTROL_UUID)
        try:
            text = value.decode("utf-8")
            print(f"📖 PRIMARY value: {text}")
        except UnicodeDecodeError:
            print(f"📖 PRIMARY value (hex): {value.hex()}")

        # Read current value from ALT
        value = await client.read_gatt_char(CHAR_CONTROL_ALT_UUID)
        try:
            text = value.decode("utf-8")
            print(f"📖 ALT value: {text}")
        except UnicodeDecodeError:
            print(f"📖 ALT value (hex): {value.hex()}")

        # Wait a bit for any notifications
        print("\n⏳ Waiting 10 seconds for notifications...")
        await asyncio.sleep(10)

        await client.stop_notify(CHAR_CONTROL_UUID)
        await client.stop_notify(CHAR_CONTROL_ALT_UUID)


async def send_command(command: str, use_alt: bool = False) -> None:
    """Send a command to the saber."""
    print(f"🔌 Connecting to {KNOWN_MAC}...")

    authorized = asyncio.Event()
    status_received = asyncio.Event()

    def alt_notification_handler(sender: int, data: bytearray) -> None:
        """Handle notifications from the secondary characteristic (0x3AB1)."""
        try:
            text = data.decode("utf-8")
            print(f"📨 ALT Notification: {text}")
            if "AccessAllowed" in text:
                print("🔓 Authorization received!")
                authorized.set()
        except UnicodeDecodeError:
            print(f"📨 ALT Notification (hex): {data.hex()}")

    def primary_notification_handler(sender: int, data: bytearray) -> None:
        """Handle notifications from the primary characteristic (0xDAE1)."""
        try:
            text = data.decode("utf-8")
            print(f"📨 Notification: {text}")
            if "HardwareVersion" in text or "PowerOn" in text:
                status_received.set()
        except UnicodeDecodeError:
            print(f"📨 Notification (hex): {data.hex()}")

    async with BleakClient(KNOWN_MAC) as client:
        print(f"✅ Connected: {client.is_connected}")

        # Enable notifications on BOTH characteristics (like the app does)
        print("📡 Enabling notifications on PRIMARY (0xDAE1)...")
        await client.start_notify(CHAR_CONTROL_UUID, primary_notification_handler)

        print("📡 Enabling notifications on ALT (0x3AB1)...")
        await client.start_notify(CHAR_CONTROL_ALT_UUID, alt_notification_handler)

        # Wait for status and authorization (with timeout)
        print("⏳ Waiting for device status and authorization (10s timeout)...")
        try:
            await asyncio.wait_for(
                asyncio.gather(status_received.wait(), authorized.wait()),
                timeout=10.0,
            )
            print("✅ Device ready!")
        except TimeoutError:
            print("⚠️ Timeout waiting for device - proceeding anyway")

        # Decide which characteristic to write to
        char_uuid = CHAR_CONTROL_ALT_UUID if use_alt else CHAR_CONTROL_UUID
        char_name = "ALT (0x3AB1)" if use_alt else "PRIMARY (0xDAE1)"

        # Send command
        data = command.encode("utf-8")
        print(f"📤 Sending to {char_name}: {command}")
        print(f"   (hex: {data.hex()})")

        # Use response=False for the ALT characteristic (WRITE NO RESPONSE)
        await client.write_gatt_char(char_uuid, data, response=not use_alt)
        print("✅ Command sent!")

        # Wait for response
        print("\n⏳ Waiting 3 seconds for response...")
        await asyncio.sleep(3)

        await client.stop_notify(CHAR_CONTROL_UUID)
        await client.stop_notify(CHAR_CONTROL_ALT_UUID)


async def send_blind_command() -> None:
    """Send commands WITHOUT notification setup - test if writes work regardless."""
    print(f"🔌 Connecting to {KNOWN_MAC} (BLIND mode - no notifications)...")

    async with BleakClient(KNOWN_MAC) as client:
        print(f"✅ Connected: {client.is_connected}")

        # Force service discovery to avoid "Service Discovery has not been performed" error
        print("📋 Discovering services...")
        services = client.services
        for service in services:
            if "3ab" in service.uuid.lower() or "dae" in service.uuid.lower():
                print(f"  Found: {service.uuid}")

        print(f"📊 MTU: {client.mtu_size}")

        # CONFIRMED: Commands use type 2, sent to 0x3AB1 with Write Command (no response)
        # This was discovered via HCI snoop capture 2026-01-28

        # Test 1: Write power on to ALT (0x3AB1) - CORRECT METHOD
        print("\n--- Test 1: Write to ALT (0x3AB1) with type 2 (CORRECT) ---")
        cmd1 = b'[2,{"PowerOn":true}]'
        print(f"📤 Sending: {cmd1.decode()}")
        try:
            await client.write_gatt_char(CHAR_CONTROL_ALT_UUID, cmd1, response=False)
            print("✅ Write succeeded (no response)")
        except Exception as e:
            print(f"❌ Write failed: {e}")

        print("⏳ Blade should ignite now! Waiting 3 seconds...")
        await asyncio.sleep(3)

        # Test 2: Write power off to ALT (0x3AB1)
        print("\n--- Test 2: Write to ALT (0x3AB1) - power off ---")
        cmd2 = b'[2,{"PowerOn":false}]'
        print(f"📤 Sending: {cmd2.decode()}")
        try:
            await client.write_gatt_char(CHAR_CONTROL_ALT_UUID, cmd2, response=False)
            print("✅ Write succeeded (no response)")
        except Exception as e:
            print(f"❌ Write failed: {e}")

        print("⏳ Blade should retract now! Waiting 3 seconds...")
        await asyncio.sleep(3)

        # Test 3: Color change
        print("\n--- Test 3: Write color to ALT (0x3AB1) ---")
        cmd3 = b'[2,{"BackgroundColor":[255,0,0]}]'
        print(f"📤 Sending: {cmd3.decode()}")
        try:
            await client.write_gatt_char(CHAR_CONTROL_ALT_UUID, cmd3, response=False)
            print("✅ Write succeeded (no response)")
        except Exception as e:
            print(f"❌ Write failed: {e}")

        await asyncio.sleep(1)
        print("🔌 Disconnecting...")


async def _cmd_power() -> None:
    """Handle power on/off command."""
    if len(sys.argv) < 3:
        print("Usage: power on|off")
        return
    state = "true" if sys.argv[2].lower() == "on" else "false"
    await send_command(f'[2,{{"PowerOn":{state}}}]', use_alt=True)


async def _cmd_color() -> None:
    """Handle color command."""
    if len(sys.argv) < 5:
        print("Usage: color R G B (0-255)")
        return
    r, g, b = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    await send_command(f'[2,{{"BackgroundColor":[{r},{g},{b}]}}]', use_alt=True)


async def _cmd_brightness() -> None:
    """Handle brightness command."""
    if len(sys.argv) < 3:
        print("Usage: brightness 0-100")
        return
    level = int(sys.argv[2])
    await send_command(f'[2,{{"Brightness":{level}}}]', use_alt=True)


async def _cmd_raw() -> None:
    """Handle raw JSON command."""
    if len(sys.argv) < 3:
        print("Usage: raw '<json>'")
        return
    await send_command(sys.argv[2])


async def _cmd_alt() -> None:
    """Handle alt characteristic command."""
    if len(sys.argv) < 3:
        print("Usage: alt '<json>'")
        return
    await send_command(sys.argv[2], use_alt=True)


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return

    commands = {
        "scan": scan_devices,
        "debug": debug_gatt,
        "read": connect_and_read,
        "power": _cmd_power,
        "color": _cmd_color,
        "brightness": _cmd_brightness,
        "raw": _cmd_raw,
        "alt": _cmd_alt,
        "blind": send_blind_command,
    }

    cmd = sys.argv[1].lower()
    handler = commands.get(cmd)
    if handler:
        await handler()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
