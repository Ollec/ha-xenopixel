# Xenopixel Lightsaber Integration for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![GitHub Release](https://img.shields.io/github/release/Ollec/ha-xenopixel.svg)](https://github.com/Ollec/ha-xenopixel/releases)
[![License](https://img.shields.io/github/license/Ollec/ha-xenopixel.svg)](LICENSE)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/6c54069910ee45e9acf11e3a0ecc4fba)](https://app.codacy.com/gh/Ollec/ha-xenopixel/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

Control your Xenopixel V3 lightsabers via Bluetooth from Home Assistant.

## Features

- Turn lightsaber on/off
- Change blade color (RGB)
- Adjust brightness
- Volume control
- Sound font selection
- Light effect selection
- Battery level monitoring
- Hardware/software version reporting
- WLED UDP sync (receive color/brightness from any WLED device on the network)
- Multi-saber support (control 2+ sabers from a single ESP32)
- Notification-driven state sync (not optimistic)
- Auto-discovery via Bluetooth

## Current Status

The **ESPHome proxy** (`esphome/`) is fully working and tested. It uses an ESP32 as a BLE-to-WiFi bridge, working around Linux BlueZ CCCD compatibility issues. See [esphome/README.md](esphome/README.md) for setup instructions.

The **Python HA integration** (`custom_components/xenopixel/`) has the protocol library and config flow implemented, but the light entity platform is not yet wired up.

## Requirements

- Home Assistant 2025.1.0 or newer
- **ESP32 board** (recommended) — acts as BLE proxy, avoids Linux BlueZ issues
- Xenopixel V3 lightsaber with Bluetooth enabled

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add `https://github.com/Ollec/ha-xenopixel` with category "Integration"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/Ollec/ha-xenopixel/releases)
2. Extract the `custom_components/xenopixel` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Automatic Discovery

If your lightsaber is powered on and within Bluetooth range, Home Assistant should automatically discover it. You'll see a notification to set it up.

### Manual Setup

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Xenopixel"
4. Follow the setup wizard

## Saber Preparation

Before using with Home Assistant, configure your lightsaber's SD card:

Edit `Set/config.ini` on the saber's SD card:

```ini
# CRITICAL: Prevent Bluetooth from turning off
DeepSleep = 999999

# Optional: Give your saber a unique name
BluetoothName = Saber_Living_Room

# Optional: Set a reasonable default volume
Vol = 50
```

## Multi-Saber Support

The ESPHome proxy supports controlling multiple sabers from a single ESP32 (up to 3, the ESP32 default GATT client limit). Each saber gets its own set of entities in Home Assistant.

### Configuration

Edit `esphome/xenopixel_simple.yaml` to configure your sabers. Each saber is defined as a package:

```yaml
packages:
  saber1: !include
    file: packages/saber.yaml
    vars:
      saber_id: saber1
      saber_name: !secret saber1_name
      saber_mac: !secret saber1_mac
  saber2: !include
    file: packages/saber.yaml
    vars:
      saber_id: saber2
      saber_name: !secret saber2_name
      saber_mac: !secret saber2_mac
```

Configure your sabers in `esphome/secrets.yaml`:

```yaml
saber1_mac: "B0:CB:D8:DB:E1:AE"
saber1_name: "Saber 1"
saber2_mac: "AA:BB:CC:DD:EE:FF"
saber2_name: "Saber 2"
```

### Adding/Removing Sabers

- **Add a saber**: Add a new package block (e.g., `saber3`), add its secrets, and add a dispatch line in the WLED lambda
- **Remove a saber**: Delete (or comment out) the package block AND its two WLED dispatch lines in the lambda
- **Single saber**: Comment out the `saber2` package block AND the two `s2` lines in the WLED lambda — both changes are needed or the build will fail

## Entities Created (ESPHome Proxy)

Each saber creates its own set of entities. For a saber named "Saber 1":

| Entity | Type | Description |
|--------|------|-------------|
| `light.xenopixel_saber_1_blade` | Light | Blade on/off, color, brightness |
| `number.xenopixel_saber_1_volume` | Number | Volume control (0-100) |
| `number.xenopixel_saber_1_sound_font` | Number | Sound font selection |
| `number.xenopixel_saber_1_light_effect` | Number | Light effect selection |
| `sensor.xenopixel_saber_1_battery` | Sensor | Battery level (%) |
| `switch.xenopixel_saber_1_wled_sync` | Switch | Enable/disable WLED UDP sync |
| `switch.xenopixel_saber_1_lockup` | Switch | Lockup effect toggle |
| `switch.xenopixel_saber_1_drag` | Switch | Drag effect toggle |
| `button.xenopixel_saber_1_clash` | Button | Trigger clash effect |
| `button.xenopixel_saber_1_blaster` | Button | Trigger blaster effect |
| `button.xenopixel_saber_1_force` | Button | Trigger force effect |

## Troubleshooting

### Saber not discovered

1. Ensure the saber is powered on (not in deep sleep)
2. Check that Bluetooth is enabled on your Home Assistant host
3. Verify the saber is within Bluetooth range (~10 meters)
4. Try using a [Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html) if your HA server is far from the saber

### Connection drops frequently

1. Check `DeepSleep` setting in `config.ini` (should be very high or disabled)
2. Move the Bluetooth adapter/proxy closer to the saber
3. Ensure no metal obstructions between adapter and saber (aluminum hilts can block signals)

### Colors don't match

The saber's LED strip may have different color ordering (RGB vs GRB). This will be addressed in future updates.

## WLED Sync

The saber can sync its color and brightness to any [WLED](https://kno.wled.ge/) device on the same network. This lets you match your lightsaber to room lighting, LED strips, or other WLED-controlled devices.

### How it works

1. Enable the **WLED Sync** switch in Home Assistant (default OFF)
2. Configure your WLED device to broadcast sync packets (Settings > Sync Interfaces > "Send notifications on change")
3. The ESP32 listens for WLED UDP notifier packets on port 21324 and applies the color/brightness to the saber

When WLED Sync is ON, Home Assistant light controls are paused so WLED drives the saber exclusively. Turn the switch OFF to resume normal HA control.

### Notes

- WiFi power save is disabled on the ESP32 to ensure reliable UDP broadcast reception
- The ESP32 shares a single 2.4GHz radio between WiFi and BLE, so occasional packet drops (~10% with 1 saber, ~15-20% with 2) are expected — the next broadcast will catch up
- WLED only broadcasts when its state changes, not continuously
- Each saber has its own WLED Sync switch — you can sync one saber to WLED while controlling the other from HA

## Development

This project uses [UV](https://docs.astral.sh/uv/) for fast, reliable dependency management.


### Setup

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (creates .venv automatically)
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install
```

### Running Checks

```bash
# Run linting
uv run ruff check .

# Run formatter check
uv run ruff format --check .

# Run type checking
uv run mypy custom_components/xenopixel

# Run Python tests
uv run pytest tests/ -v

# Build and run C++ tests (for the ESPHome XenopixelLight component)
cd tests/cpp && cmake -B build && cmake --build build && ctest --test-dir build --output-on-failure

# Run all Python checks
uv run ruff check . && uv run ruff format --check . && uv run pytest tests/ -v
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration. Xenopixel and related trademarks belong to their respective owners. This project is not affiliated with or endorsed by LGT Saberstudio or Damien Technology.
