# Xenopixel Lightsaber ESPHome Proxy

[![GitHub Release](https://img.shields.io/github/release/Ollec/ha-xenopixel.svg)](https://github.com/Ollec/ha-xenopixel/releases)
[![License](https://img.shields.io/github/license/Ollec/ha-xenopixel.svg)](LICENSE)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/6c54069910ee45e9acf11e3a0ecc4fba)](https://app.codacy.com/gh/Ollec/ha-xenopixel/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

Control your Xenopixel V3 lightsabers via an ESP32 BLE-to-WiFi proxy, with native Home Assistant integration through ESPHome.

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

## Requirements

- **ESP32 board** (any variant with BLE support) — acts as BLE-to-WiFi proxy
- [ESPHome](https://esphome.io/) installed (`pip install esphome`)
- Home Assistant with ESPHome integration
- Xenopixel V3 lightsaber with Bluetooth enabled

## Why ESP32?

Linux BlueZ blocks CCCD descriptor writes required by the Xenopixel BLE protocol. The ESP32's BLE stack handles this correctly. See [docs/BLE_COMPATIBILITY.md](docs/BLE_COMPATIBILITY.md) for details.

## Installation

1. Get an ESP32 board (any variant with BLE)
2. Install ESPHome: `pip install esphome`
3. Copy `esphome/secrets.yaml.example` to `esphome/secrets.yaml`
4. Fill in your WiFi credentials, API key, and saber MAC address(es)
5. Compile and flash the file matching your saber count:

```bash
# Single saber
cd esphome && esphome run xenopixel_1saber.yaml

# Two sabers
cd esphome && esphome run xenopixel_2sabers.yaml
```

6. The ESP32 device will appear automatically in Home Assistant via ESPHome

## Multi-Saber Support

The ESPHome proxy supports controlling multiple sabers from a single ESP32 (up to 3, the ESP32 default GATT client limit). Each saber gets its own set of entities — only real sabers are compiled in, so there are no phantom entities.

Configure your sabers in `esphome/secrets.yaml`:

```yaml
# Saber 1 (required)
saber1_mac: "AA:BB:CC:DD:EE:FF"
saber1_name: "Saber 1"

# Saber 2 (only needed for xenopixel_2sabers.yaml)
saber2_mac: "11:22:33:44:55:66"
saber2_name: "Saber 2"
```

### Adding More Sabers

To add a 3rd saber, create `xenopixel_3sabers.yaml` with an additional saber package include and add `saber3_mac`/`saber3_name` to `secrets.yaml`. No code changes needed.

## Entities Created

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

### Saber not connecting

1. Ensure the saber is powered on (not in deep sleep)
2. Verify the saber is within Bluetooth range (~10 meters)
3. Check the ESP32 logs via `esphome logs xenopixel_1saber.yaml`

### Connection drops frequently

1. Check `DeepSleep` setting in `config.ini` (should be very high or disabled)
2. Move the ESP32 closer to the saber
3. Ensure no metal obstructions between ESP32 and saber (aluminum hilts can block signals)


## WLED Sync

The saber can sync its color and brightness to any [WLED](https://kno.wled.ge/) device on the same network. This lets you match your lightsaber to room lighting, LED strips, or other WLED-controlled devices.

### How it works

1. Enable the **WLED Sync** switch for a saber (default OFF)
2. Configure your WLED device to broadcast sync packets (Settings > Sync Interfaces > "Send notifications on change")
3. The ESP32 listens for WLED UDP notifier packets on port 21324 and applies the color/brightness to the saber

When WLED Sync is ON, normal light controls are paused so WLED drives the saber exclusively. Turn the switch OFF to resume normal control.

### Best use case

WLED Sync works best with **solid colors** and **slow transitions**. Setting a WLED device to a solid color reliably syncs to the saber within a second. This is ideal for matching a lightsaber to room lighting, themed scenes, or manual color changes.

### Limitations

**Animated effects are best-effort.** WLED's UDP notifier protocol (port 21324) broadcasts the segment's primary color when it changes — not the per-pixel rendered output on every frame. For animated effects (rainbow, chase, etc.), the saber receives color updates only when the effect internally cycles the primary color, which varies by effect and speed. Some effects update frequently, others rarely.

**UDP packet loss is expected.** The ESP32 shares a single 2.4GHz radio between WiFi and BLE. Active BLE connections preempt WiFi reception, and UDP provides no retransmission — missed packets are simply lost. Observed packet loss:
- ~10% with 1 saber connected
- ~15-20% with 2 sabers connected

Combined with the fact that WLED only broadcasts on change (not continuously), the saber may lag behind fast-moving effects or miss brief color transitions entirely. The next received packet will catch up.

**This is a protocol-level constraint**, not a software bug. WLED's notifier protocol was designed for syncing state between WLED controllers, not for streaming real-time animation data. Streaming protocols like DDP or E1.31 send per-pixel data every frame, but a lightsaber is a single-color device with ~100ms BLE command latency, so frame-accurate sync isn't achievable regardless.

### Other notes

- WiFi power save is disabled on the ESP32 to ensure reliable UDP broadcast reception
- Each saber has its own WLED Sync switch — you can sync one saber to WLED while controlling the other normally
- The saber keepalive is automatically paused during WLED sync to avoid interference

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
uv run mypy src/xenopixel_ble

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

This is an unofficial project. Xenopixel and related trademarks belong to their respective owners. This project is not affiliated with or endorsed by LGT Saberstudio or Damien Technology.
