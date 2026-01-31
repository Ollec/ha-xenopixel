# BLE Compatibility Issues and ESP32 Solution

This document outlines the Bluetooth Low Energy (BLE) compatibility issues discovered while developing the Xenopixel lightsaber integration for Home Assistant, and explains why an ESP32 proxy approach is the recommended solution.

## Summary

**Problem**: Linux BlueZ cannot enable BLE notifications on the Xenopixel saber due to CCCD write permission errors.

**Impact**: Without notifications, the device ignores all commands - the blade won't ignite, change color, or respond in any way.

**Solution**: Use an ESP32 as a BLE-to-Home-Assistant proxy. The ESP32's BLE stack handles this device correctly.

---

## The Technical Issue

### What We Discovered

Through extensive testing (see [PROTOCOL.md](../PROTOCOL.md)), we confirmed the Xenopixel BLE protocol:

| Direction | Message Type | Characteristic | Description |
|-----------|--------------|----------------|-------------|
| Commands TO device | `2` | `0x3AB1` | Power, color, brightness, volume, sound font, light effect |
| Notifications FROM device | `3` | `0xDAE1` | Status updates |

**Critical Finding**: The device requires **notifications to be enabled** before it will accept commands. This is done by writing `0x0100` to the CCCD (Client Characteristic Configuration Descriptor) on each characteristic.

### The BlueZ Problem

When connecting from Linux using bleak/BlueZ, CCCD writes fail with:

```
[org.bluez.Error.NotPermitted] Write not permitted
```

This occurs even though:
- ✅ We can connect to the device
- ✅ We can read characteristics
- ✅ We can write to characteristics (commands)
- ❌ But the device **ignores commands** because notifications weren't enabled

### Why This Happens

The Xenopixel saber's BLE firmware requires **encrypted CCCD writes**. Specifically:

1. The GATT server on the saber sets security permissions on CCCD descriptors
2. These permissions require an authenticated/encrypted connection
3. Linux BlueZ's handling of LE Secure Connections varies by version
4. BlueZ refuses the CCCD write rather than automatically establishing encryption

**Android works perfectly** because:
- Android's Bluetooth stack handles security negotiation automatically
- It establishes encryption transparently during the connection process
- CCCD writes succeed, enabling notifications
- Commands then work as expected

---

## Testing Performed

### Environment
- **OS**: Ubuntu Linux (kernel reported via uname)
- **BLE Library**: bleak (Python)
- **BlueZ**: System version (varies)

### Tests Run

1. **Direct Write Tests**
   - Writes to 0x3AB1 and 0xDAE1 succeed at BLE level
   - Blade does NOT respond (no ignite/retract)
   - Confirmed: writes alone are insufficient

2. **Notification Enable Tests**
   - `bleak.start_notify()` reports success
   - Underlying CCCD write fails silently in some cases
   - Explicit CCCD writes fail with "NotPermitted"
   - **No notifications ever received**

3. **Pairing Tests**
   - Removing and re-pairing doesn't resolve the issue
   - Explicit pairing with encryption levels attempted
   - BlueZ `btmgmt` secure connection settings tried
   - **Issue persists**

4. **Diagnostic Analysis** ([diagnose_ble.py](../tools/diagnose_ble.py))
   - Confirmed CCCD handles exist (13 for 0xDAE1, 17 for 0x3AB1)
   - Confirmed characteristics have "notify" property
   - Confirmed writes to CCCD return "NotPermitted"

### Confirmed Working

| Platform | BLE Stack | Result |
|----------|-----------|--------|
| Android | Android Bluetooth | ✅ Works perfectly |
| Linux | BlueZ via bleak | ❌ CCCD writes blocked |
| ESP32 | ESP-IDF BLE | ✅ Works (confirmed 2026-01-30) |

---

## Why ESP32?

### The ESP32 Advantage

The ESP32's BLE stack (ESP-IDF/NimBLE):
1. **Handles security automatically** - Negotiates encryption when needed
2. **No CCCD permission issues** - Writes succeed where BlueZ fails
3. **Proven compatibility** - Many similar devices work via ESP32 proxies
4. **ESPHome integration** - Native Home Assistant support

### Architecture

```
┌─────────────────┐     WiFi/API      ┌─────────────┐      BLE       ┌────────────┐
│  Home Assistant │ ◄───────────────► │    ESP32    │ ◄────────────► │   Saber    │
│                 │                   │  (ESPHome)  │                │ (Xenopixel)│
└─────────────────┘                   └─────────────┘                └────────────┘
```

### Benefits

1. **Works reliably** - ESP32 BLE stack handles the device correctly
2. **Extended range** - Place ESP32 near saber, connect via WiFi from anywhere
3. **Native HA support** - ESPHome integrates seamlessly with Home Assistant
4. **Low cost** - ESP32 boards cost ~$5-10
5. **Low power** - Can be powered by USB, runs continuously

---

## Alternative Approaches Considered

### 1. Different BlueZ Version
- **Effort**: Medium (system changes)
- **Risk**: May break other Bluetooth functionality
- **Result**: Not tested, likely won't resolve fundamental security handling

### 2. Raspberry Pi
- **Effort**: Medium (different hardware)
- **Risk**: May have same BlueZ issues
- **Result**: Untested, but RPi uses same BlueZ stack

### 3. Raw D-Bus Calls
- **Effort**: High (bypass bleak)
- **Risk**: Complex, fragile
- **Result**: CCCD permissions are enforced at BlueZ level

### 4. Custom BlueZ Configuration
- **Effort**: High (deep system changes)
- **Risk**: May require kernel patches
- **Result**: Not practical for end users

### 5. ESP32 Proxy ✅ **RECOMMENDED**
- **Effort**: Low (flash firmware)
- **Risk**: Low (isolated system)
- **Result**: Known to work for similar devices

---

## Getting Started with ESP32

See the ESPHome configurations in the `esphome/` directory:

- **[xenopixel_simple.yaml](../esphome/xenopixel_simple.yaml)** - Full ESPHome config with switches, number inputs, notification-driven state sync

### Quick Start

1. Get an ESP32 board (any variant with BLE)
2. Install ESPHome: `pip install esphome`
3. Create `secrets.yaml` with your WiFi credentials
4. Update the `saber_mac` in the YAML file
5. Compile and flash: `esphome run xenopixel_simple.yaml`
6. Add the ESPHome device to Home Assistant

---

## Future Work

1. **Create Home Assistant integration** - HACS-compatible native light entity using the Python protocol library
2. **Document setup process** - Step-by-step guide with photos

---

## References

- [PROTOCOL.md](../PROTOCOL.md) - Full BLE protocol documentation
- [tools/](../tools/) - Test scripts used for debugging
- [ESPHome BLE Client](https://esphome.io/components/ble_client.html) - ESPHome BLE documentation
- [BlueZ GATT](http://www.yourwarrantyisvoid.net/2020/08/28/bluez-gatt-and-ble-security/) - BlueZ GATT security article
