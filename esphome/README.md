# ESPHome Configuration for Xenopixel Lightsaber

This directory contains ESPHome configurations to use an ESP32 as a BLE proxy for controlling Xenopixel lightsabers from Home Assistant.

## Why ESP32?

Linux BlueZ has compatibility issues with the Xenopixel saber's BLE security requirements. The ESP32's BLE stack handles these correctly. See [BLE_COMPATIBILITY.md](../docs/BLE_COMPATIBILITY.md) for technical details.

## Hardware Requirements

- **ESP32 board** - Any variant with BLE support:
  - ESP32-DevKitC (~$10)
  - ESP32-WROOM (~$5)
  - ESP32-C3 (~$5)
  - NodeMCU-32S (~$8)
- **USB cable** for power and initial flashing
- **5V USB power adapter** for permanent installation

## Quick Start

### 1. Install ESPHome

```bash
pip install esphome
```

Or use the ESPHome Dashboard addon in Home Assistant.

### 2. Create Secrets File

```bash
cp secrets.yaml.example secrets.yaml
```

Edit `secrets.yaml` with your credentials:

```yaml
wifi_ssid: "YourWiFiNetwork"
wifi_password: "YourWiFiPassword"
ap_password: "FallbackPassword123"
api_encryption_key: "generate_with_openssl_rand_-base64_32"
ota_password: "YourOTAPassword"
```

Generate an API encryption key:
```bash
openssl rand -base64 32
```

### 3. Update Saber MAC Address

Edit `xenopixel_simple.yaml` and update the MAC address:

```yaml
substitutions:
  saber_mac: "B0:CB:D8:DB:E1:AE"  # ← Your saber's MAC
```

Find your saber's MAC address using nRF Connect on your phone, or from the earlier test scripts.

### 4. Compile and Flash

**First time (via USB):**
```bash
esphome run xenopixel_1saber.yaml
```

Select your serial port when prompted.

**Subsequent updates (via WiFi OTA):**
```bash
esphome run xenopixel_1saber.yaml
```

ESPHome will automatically detect and use OTA if available.

### 5. Add to Home Assistant

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for **ESPHome**
4. Enter the ESP32's IP address or hostname (`xenopixel-saber.local`)
5. Enter the API encryption key when prompted

## How It Works

The ESP32 connects to the saber via BLE and performs an authorization handshake:

1. **Connect** to the saber's MAC address
2. **Enable indications** on the Service Changed characteristic (0x2A05)
3. **Send HandShake** message to DAE1: `[2,{"HandShake":"HelloDamien"}]`
4. **Send Authorize** message to 3AB1: `[2,{"Authorize":"SaberOfDamien"}]`
5. **Saber responds** with a full status dump and `[3,{"Authorize":"AccessAllowed"}]`

After authorization, the ESP32 can send commands and receives status notifications on DAE1. All controls are gated behind the authorization check — commands won't be sent until the saber has responded with `AccessAllowed`.

State is synced from BLE notifications, not optimistic — the blade switch, volume, brightness, and other entities reflect the saber's actual state.

See [PROTOCOL.md](../PROTOCOL.md) for the full protocol specification.


## Example Automations


### Flash saber when doorbell rings
```yaml
automation:
  - alias: "Saber flash on doorbell"
    trigger:
      - platform: state
        entity_id: binary_sensor.doorbell
        to: "on"
    action:
      - repeat:
          count: 3
          sequence:
            - service: light.turn_on
              target:
                entity_id: switch.xenopixel_saber_blade
            - delay: 0.5
            - service: light.turn_off
              target:
                entity_id: switch.xenopixel_saber_blade
            - delay: 0.5
```

## Troubleshooting

### ESP32 won't connect to saber

1. **Check MAC address** - Ensure the MAC in the YAML matches your saber
2. **Check distance** - ESP32 should be within ~10m of saber
3. **Check saber is on** - The saber must be powered on (not in deep sleep)
4. **Check logs**: `esphome logs xenopixel_simple.yaml`

### Commands not working

1. **Check authorization** - The `Authorized` sensor must be ON (not just `Connected`)
2. **Wait for handshake** - Authorization completes ~3 seconds after BLE connects
3. **Check logs**: look for `*** SABER AUTHORIZED! Commands now accepted ***`
4. If you see `Cannot turn on blade - saber not authorized yet!`, the handshake hasn't completed

### Can't flash ESP32

1. **Hold BOOT button** while connecting USB
2. **Check USB cable** - Must be data-capable, not charge-only
3. **Install drivers** - CP2102 or CH340 drivers may be needed

### WiFi connection issues

1. **Check credentials** in `secrets.yaml`
2. **Check signal** - Move ESP32 closer to router
3. **Use 2.4GHz** - ESP32 doesn't support 5GHz WiFi

## Custom Light Component

The `components/xenopixel_light/` directory contains a custom ESPHome `LightOutput` that integrates with Home Assistant's native light entity system. Instead of ESPHome's default combined RGB output, this component sends separate BLE commands for power, brightness, and color to match the Xenopixel protocol.

Key behaviors:
- **Redundancy checks** — Skips BLE writes when the value hasn't changed
- **Color debouncing** — Suppresses rapid color changes (100ms minimum interval)
- **Brightness recovery** — ESPHome bakes brightness into RGB values; the component divides it back out to send correct raw color values to the saber
- **Guard conditions** — Blocks all commands while syncing from saber notifications or before authorization completes

The component is tested with 18 host-based C++ unit tests (GoogleTest) in `tests/cpp/`. These tests use mock stubs for all ESPHome and ESP-IDF types, so no ESP32 hardware is required:

```bash
cd tests/cpp && cmake -B build && cmake --build build && ctest --test-dir build --output-on-failure
```

## Protocol Reference

### Authorization (sent automatically on connect)

| Step | Characteristic | JSON |
|------|----------------|------|
| HandShake | `0xDAE1` | `[2,{"HandShake":"HelloDamien"}]` |
| Authorize | `0x3AB1` | `[2,{"Authorize":"SaberOfDamien"}]` |

### Commands (sent to `0x3AB1` after authorization)

| Command | JSON |
|---------|------|
| Power ON | `[2,{"PowerOn":true}]` |
| Power OFF | `[2,{"PowerOn":false}]` |
| Set Color | `[2,{"BackgroundColor":[R,G,B]}]` |
| Set Brightness | `[2,{"Brightness":0-100}]` |
| Set Volume | `[2,{"Volume":0-100}]` |
| Set Sound Font | `[2,{"CurrentSoundPackageNo":N}]` (1-34) |
| Set Light Effect | `[2,{"CurrentLightEffect":N}]` |
| Clash (one-shot) | `[2,{"Clash":true}]` |
| Blaster (one-shot) | `[2,{"Blaster":true}]` |
| Force (one-shot) | `[2,{"Force":true}]` |
| Lockup ON/OFF | `[2,{"Lockup":true/false}]` |
| Drag ON/OFF | `[2,{"Drag":true/false}]` |

See [PROTOCOL.md](../PROTOCOL.md) for full protocol documentation.
