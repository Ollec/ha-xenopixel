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

## Entities Created (ESPHome Proxy)

See [esphome/README.md](esphome/README.md) for the full entity list. Key entities:

| Entity | Type | Description |
|--------|------|-------------|
| `switch.xenopixel_saber_blade` | Switch | Blade on/off (notification-driven) |
| `number.xenopixel_saber_*` | Number | Color, brightness, volume, sound font, light effect |
| `sensor.xenopixel_saber_battery` | Sensor | Battery level (%) |

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

## Development

This project uses [UV](https://docs.astral.sh/uv/) for fast, reliable dependency management.

See [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) for the development roadmap.

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

# Run tests
uv run pytest tests/ -v

# Run all checks
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
