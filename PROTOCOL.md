# Xenopixel V3 BLE Protocol Documentation

This document describes the Bluetooth Low Energy (BLE) protocol used by Xenopixel V3 lightsaber soundboards.

## Device Discovery

### Advertisement Data
- **Device Name**: `SABER` (or configured name from config.ini)
- **MAC Address**: Device-specific (e.g., `B0:CB:D8:DB:E1:AE`)

## GATT Structure

### Services

| Service | UUID | Description |
|---------|------|-------------|
| Generic Access | `0x1800` | Standard BLE device info |
| Generic Attribute | `0x1801` | Standard BLE GATT |
| **Primary Control** | **`0xDAE0`** | **Main control service (JSON protocol)** |
| **Secondary Control** | **`0x3AB0`** | **Authorization service** |

### Primary Control Service (`0xDAE0`)

| Characteristic | UUID | Properties | Description |
|----------------|------|------------|-------------|
| **Control** | `0xDAE1` | NOTIFY, READ, WRITE | Send/receive JSON commands |

### Secondary Control Service (`0x3AB0`)

| Characteristic | UUID | Properties | Description |
|----------------|------|------------|-------------|
| **Control** | `0x3AB1` | NOTIFY, READ, WRITE NO RESPONSE | Authorization channel |

### Characteristic Descriptors

| Descriptor | UUID | Description |
|------------|------|-------------|
| CCCD | `0x2902` | Client Characteristic Configuration (enable notifications) |

### GATT Handle Table (confirmed via HCI snoop + ESP32 discovery)

| Handle | Type | UUID | Description |
|--------|------|------|-------------|
| 1 | Service | `0x1800` | Generic Access |
| 2-3 | Char | `0x2A00` | Device Name |
| 4-5 | Char | `0x2A01` | Appearance |
| 6 | Service | `0x1801` | Generic Attribute |
| 7-8 | Char | `0x2A05` | Service Changed [Indication] |
| 9 | Descriptor | `0x2902` | CCCD for 0x2A05 |
| 10 | Service | `0xDAE0` | Primary Control |
| 11-12 | Char | `0xDAE1` | Control [Notify, Read, Write] |
| 13 | Descriptor | `0x2902` | CCCD for 0xDAE1 |
| 14 | Service | `0x3AB0` | Secondary Control |
| 15-16 | Char | `0x3AB1` | Control [Notify, Read, Write No Response] |
| 17 | Descriptor | `0x2902` | CCCD for 0x3AB1 |

## Protocol Format

The Xenopixel V3 uses a **JSON-based protocol** over BLE.

### Message Structure
```json
[message_type, {"key": value, ...}]
```

- **Message Type `2`**: Commands sent TO device
- **Message Type `3`**: Notifications/responses FROM device
- **Parameters**: JSON object with command/status data
- **Encoding**: UTF-8 text

## Commands (CONFIRMED via HCI Snoop Capture 2026-01-28)

| Direction | Message Type | Characteristic | ATT Opcode |
|-----------|--------------|----------------|------------|
| **Commands TO device** | `2` | `0x3AB1` | Write Command (0x52, no response) |
| **Notifications FROM device** | `3` | `0xDAE1` | Notify |

### Power Control

**Turn blade ON (ignite):**
```json
[2,{"PowerOn":true}]
```

**Turn blade OFF (retract):**
```json
[2,{"PowerOn":false}]
```

### Color Control

**Set background color (RGB array):**
```json
[2,{"BackgroundColor":[255,0,0]}]
```
- Values are 0-255 for each RGB component
- Example: `[255,0,0]` = red

### Brightness Control

**Set brightness:**
```json
[2,{"Brightness":50}]
```
- Value range: 0-100

## Status Notifications

The device sends status updates via notifications on `0xDAE1`.

### Power State Notification
```json
[3,{"PowerOn":true}]   // Blade is on
[3,{"PowerOn":false}]  // Blade is off
```

### Battery Level
```json
[3,{"Power":63}]
```
- Value is percentage (e.g., 63 = 63% battery)

### Full Device Status
The device reports comprehensive status including:

| Parameter | Type | Description |
|-----------|------|-------------|
| `PowerOn` | boolean | Blade on/off state |
| `Power` | int | Battery percentage |
| `HardwareVersion` | string | Hardware version |
| `SoftwareVersion` | string | Software version |
| `CurrentSoundPackageNo` | int | Active sound font number |
| `TotalSoundPackage` | int | Total available sound fonts |
| `CurrentLightEffect` | int | Active blade effect (1-9) |
| `BackgroundColor` | [R,G,B] | Current blade color |
| `Brightness` | int | Current brightness (0-100) |
| `Volume` | int | Current volume level |

### Example Full Status
```json
[3,{"HardwareVersion":"1.0","SoftwareVersion":"3.2.1","Power":63,"PowerOn":false,"CurrentSoundPackageNo":1,"TotalSoundPackage":10,"CurrentLightEffect":0,"BackgroundColor":[255,153,18],"Brightness":100,"Volume":50}]
```

## Authorization Handshake (CONFIRMED via HCI Snoop 2026-01-30)

Authorization requires an **active handshake** - the client must send two messages:

### Step 1: Enable indications on 0x2A05 (Service Changed)
Write `0x0200` to the CCCD descriptor (handle 9) of characteristic 0x2A05 in service 0x1801.

### Step 2: Send HandShake to DAE1
```json
[2,{"HandShake":"HelloDamien"}]
```
Written to `0xDAE1` using ATT Write Request (0x12, with response).

### Step 3: Send Authorize to 3AB1
```json
[2,{"Authorize":"SaberOfDamien"}]
```
Written to `0x3AB1` using ATT Write Command (0x52, no response).

### Step 4: Saber responds with full status dump + authorization
The saber sends (all on `0xDAE1` except authorization):
1. Full status with `HardwareVersion`, `SoftwareVersion`, `Power`, etc.
2. Configuration dump with `ButtonNum`, `Brightness`, blade settings, etc.
3. Settings dump with `SwingSensitivity`, modes, `HandShake:"OK"`

Then on `0x3AB1`:
```json
[3,{"Authorize":"AccessAllowed"}]
```

**Note:** "HelloDamien" and "SaberOfDamien" appear to be hardcoded in the Xeno Configurator app (Damien = Xenopixel developer). These values work for all Xenopixel V3 sabers tested.

## Keepalive / DeepSleep Prevention

The saber has a configurable DeepSleep timer. When no BLE activity occurs for that duration, the saber powers off to save battery.

The ESP32 proxy sends a periodic keepalive command (default: every 30 seconds) to prevent this while the saber is in range. The keepalive re-sends the current brightness value — this is idempotent and causes no visible change on the saber.

When the saber leaves BLE range, the connection drops and keepalives stop, allowing the saber to enter DeepSleep naturally after its configured timeout.

The keepalive interval is adjustable (0-300 seconds) via a Home Assistant number entity. Setting it to 0 disables keepalives.

## Capture Sessions

### Session 1: 2026-01-28 (nRF Logger - notifications only)

**Tools:** nRF Connect for Android, nRF Logger, Xeno Configurator app

Captured notifications from device, which confirmed the JSON protocol format
and message type 3 for responses. See `references/Log_2026-01-28*.txt`.

### Session 2: 2026-01-28 (HCI Snoop - full bidirectional capture)

**Tools:** Android HCI snoop log (`btsnoop_hci.log`), tshark/Wireshark

Captured the complete bidirectional traffic including write commands. Key discoveries:
- Commands use message type `2` (not `3`)
- Commands go to `0x3AB1` via Write Command (ATT opcode 0x52, no response)
- The HandShake goes to `0xDAE1` via Write Request (ATT opcode 0x12, with response)
- Authorization requires an active handshake (see Authorization Handshake section above)

**Analyzing the HCI snoop log:**
```bash
# Extract ATT Write Requests (0x12) and Write Commands (0x52):
tshark -r btsnoop_hci.log \
  -Y "btatt.opcode == 0x12 || btatt.opcode == 0x52" \
  -T fields -e frame.number -e btatt.opcode -e btatt.handle -e btatt.value

# Extract Handle Value Indications (0x1d) and Notifications (0x1b):
tshark -r btsnoop_hci.log \
  -Y "btatt.opcode == 0x1b || btatt.opcode == 0x1d" \
  -T fields -e frame.number -e btatt.opcode -e btatt.handle -e btatt.value
```

### Session 3: 2026-01-30 (ESPHome ESP32 - working implementation)

**Tools:** ESP32 running ESPHome, serial log output

Confirmed the complete connection and authorization flow working end-to-end
from ESP32 to saber via BLE. Full handshake completes in ~1 second after
connection is established.

## Notes

- **Commands** use message type `2`, **notifications** use message type `3`
- Commands are sent to `0x3AB1` using ATT Write Command (no response)
- The HandShake message is an exception: sent to `0xDAE1` using ATT Write Request (with response)
- Notifications are received from `0xDAE1`
- Device advertises as "SABER" (configurable via config.ini)
- Service UUID `0xDAE0` can be used for discovery
- The `Power` parameter is battery level, NOT power control
- Power control uses `PowerOn` with boolean value
- Authorization handshake strings ("HelloDamien", "SaberOfDamien") are hardcoded in the Xeno Configurator app

### Resolved Questions

1. **Do write commands use the same format as notifications?** (2026-01-28)
   - **NO!** Commands use type `2`, notifications use type `3`

2. **Which characteristic receives commands?** (2026-01-28)
   - `0x3AB1` (secondary) receives commands via Write Command (no response)
   - `0xDAE1` (primary) sends notifications (and receives HandShake)

3. **Why did commands fail from Linux?** (2026-01-28)
   - We were sending wrong message type (`3` instead of `2`)
   - We were writing to wrong characteristic (`0xDAE1` instead of `0x3AB1`)

4. **How does authorization work?** (2026-01-30)
   - The client must actively send a HandShake + Authorize message pair
   - Just enabling CCCDs/notifications is NOT sufficient
   - See "Authorization Handshake" section above for the full protocol

5. **Why didn't ESPHome get authorization?** (2026-01-30)
   - ESPHome's `get_characteristic()` only finds characteristics registered by child components
   - The 0x1801/0x2A05 service was not in ESPHome's internal map
   - Fixed by using ESP-IDF GATTC cache APIs (`esp_ble_gattc_get_service`, etc.) directly
   - Additionally, the HandShake and Authorize messages were never being sent

## Known Issues

### Linux BlueZ Notification Problem

When connecting from Linux using bleak/BlueZ, CCCD writes fail with:
```
[org.bluez.Error.NotPermitted] Write not permitted
```

**Recommended workaround:** Use an ESP32 running ESPHome as a BLE-to-WiFi proxy.
The ESP32 BLE stack handles CCCDs and the authorization handshake correctly.
See the `esphome/` directory for working configurations.

**Tested platforms:**
- ❌ Linux (Ubuntu/BlueZ via bleak) - CCCD writes fail
- ✅ Android (nRF Connect, Xeno Configurator) - works perfectly
- ✅ ESP32 (ESPHome) - works perfectly (confirmed 2026-01-30)

## References

- See [references/Agent_review.md](references/Agent_review.md) for initial technical analysis
- See [references/Log_2026-01-28 17_33_07_on_off_twice.txt](references/Log_2026-01-28%2017_33_07_on_off_twice.txt) for raw nRF Logger capture
- See [references/Log_2026-01-28_18_10_25_onOff_color.txt](references/Log_2026-01-28_18_10_25_onOff_color.txt) for nRF Logger with color changes
- [nRF Connect](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp) for GATT exploration
