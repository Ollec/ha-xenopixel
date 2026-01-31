# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom integration + ESPHome proxy for controlling Xenopixel V3 lightsabers via BLE. Two parallel approaches:

- **`custom_components/xenopixel/`** — Python-based HA integration using bleak (in development, light entity not yet implemented)
- **`esphome/`** — ESP32 BLE-to-WiFi proxy configs that work today (workaround for Linux BlueZ CCCD issues)

## Commands

```bash
# Install dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run tests with coverage (CI enforces 80% minimum)
uv run pytest --cov=custom_components/xenopixel --cov-report=term-missing --cov-fail-under=80

# Run a single test file
uv run pytest tests/test_protocol.py -v

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy custom_components/xenopixel

# ESPHome compile (requires esphome installed via uv tool)
cd esphome && esphome compile xenopixel_simple.yaml

# ESPHome compile + flash
cd esphome && esphome run xenopixel_simple.yaml
```

## Architecture

### BLE Protocol

Commands are UTF-8 JSON arrays over BLE GATT: `[message_type, {params}]`
- **Type 2** = commands TO saber (written to characteristics)
- **Type 3** = notifications FROM saber

Two separate GATT services are used:
- **0xDAE0 / 0xDAE1** — Primary service. Receives status notifications. HandShake sent here.
- **0x3AB0 / 0x3AB1** — Secondary service. Commands (PowerOn, Color, Brightness, Volume, SoundFont, LightEffect) sent here. Authorization sent here. AccessAllowed received here.

### Authorization Handshake (required before any commands)

1. Enable indications on **0x2A05** (Service Changed) — write `[0x02, 0x00]` to its CCCD descriptor
2. Enable notifications on **0xDAE1** and **0x3AB1** (standard CCCD writes)
3. Send `[2,{"HandShake":"HelloDamien"}]` to **0xDAE1**
4. Send `[2,{"Authorize":"SaberOfDamien"}]` to **0x3AB1**
5. Saber responds with full status dump on DAE1, then `[3,{"Authorize":"AccessAllowed"}]` on 3AB1

### Python Integration (`custom_components/xenopixel/`)

- `xenopixel_ble/protocol.py` — Encoder/decoder for all BLE commands and responses. `XenopixelProtocol` has static methods for each command. `XenopixelState` dataclass holds parsed device state.
- `xenopixel_ble/const.py` — BLE UUIDs, message types, parameter names, authorization values.
- `config_flow.py` — HA config flow with Bluetooth auto-discovery (scans for service UUID 0xDAE0).
- `__init__.py` — Integration entry point. No platforms wired up yet.

### ESPHome Proxy (`esphome/`)

- `xenopixel_simple.yaml` — Active config. Uses switches, number inputs, and preset buttons. Contains the full authorization lambda in `on_connect` that uses ESP-IDF GATTC APIs directly to write the 0x2A05 CCCD. Includes volume, sound font, light effect controls and notification-driven state sync.
- `secrets.yaml` — WiFi/API credentials (gitignored).

### Tools (`tools/`)

- `diagnose_ble.py` — BLE diagnostics (BlueZ version, kernel modules, bonding state)
- `parse_btsnoop.py` — HCI snoop log parser for protocol analysis
- `test_saber.py` — General saber test tool (scan, read, power, color, brightness)

### Key Technical Constraint

Linux BlueZ blocks CCCD descriptor writes with "NotPermitted" for this device. The ESP32's BLE stack handles this correctly. See `docs/BLE_COMPATIBILITY.md` for the full analysis.

## Key Reference Documents

- **`PROTOCOL.md`** — Complete BLE protocol specification with all known commands and capture sessions
- **`docs/BLE_COMPATIBILITY.md`** — Why Linux BlueZ fails and the ESP32 solution
- **`docs/DEVELOPMENT_PLAN.md`** — Development roadmap
- **`references/Agent_review.md`** — Deep technical analysis of the Xenopixel BLE protocol
