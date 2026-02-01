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

# Run Python tests
uv run pytest

# Run Python tests with coverage (CI enforces 80% minimum)
uv run pytest --cov=custom_components/xenopixel --cov-report=term-missing --cov-fail-under=80

# Run a single test file
uv run pytest tests/test_protocol.py -v

# Build and run C++ tests (requires cmake and g++)
cd tests/cpp && cmake -B build && cmake --build build && ctest --test-dir build --output-on-failure

# Generate C++ coverage locally (requires lcov)
cd tests/cpp && lcov --capture --directory build --output-file coverage.info --include '*/xenopixel_light/*'

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy custom_components/xenopixel

# Code complexity (CI thresholds: CCN 15, length 100, args 6)
uv run lizard custom_components/xenopixel/ -C 15 -L 100 -a 6 -w -i 0

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

- `xenopixel_simple.yaml` — Thin orchestrator config. Contains device settings, WiFi, shared infrastructure, WLED UDP listener, and `packages:` includes for each saber. WiFi power save is disabled (`power_save_mode: NONE`) to ensure reliable UDP broadcast reception.
- `packages/saber.yaml` — Per-saber template. Contains all entities for one saber (BLE client, authorization, sensors, light, numbers, buttons, switches). Uses `${saber_id}`, `${saber_name}`, `${saber_mac}` variables for text substitution via ESPHome's `packages:` with `vars:`.
- `components/xenopixel_light/xenopixel_light.h` — Custom ESPHome `LightOutput` component. Sends separate BLE commands for power, brightness, and color (instead of ESPHome's combined RGB values). Includes redundancy checks (skips unchanged values), color debouncing (100ms), brightness recovery (divides out ESPHome's baked-in brightness), guard conditions (blocks commands while syncing or unauthorized), and WLED support (`apply_wled_packet()` parses WLED notifier protocol, `is_wled_active()` getter for external dispatch).
- `components/xenopixel_light/light.py` — ESPHome code generation for the component. Depends on `ble_client`.
- `secrets.yaml` — WiFi/API credentials and saber MAC addresses (gitignored).

#### Multi-Saber Architecture

The ESPHome config uses `packages:` with `vars:` (ESPHome 2025.3.0+) to support multiple sabers from a single ESP32. Each package include gets text substitution before C++ compilation:

```yaml
packages:
  saber1: !include
    file: packages/saber.yaml
    vars:
      saber_id: saber1
      saber_name: !secret saber1_name
      saber_mac: !secret saber1_mac
```

Entity naming: IDs use `${saber_id}_<suffix>` (e.g., `saber1_light`), names use `"${friendly_name} ${saber_name} <Entity>"` (e.g., "Xenopixel Saber 1 Blade").

WLED UDP sync uses a single listener in the main YAML that dispatches packets to all sabers with WLED active. Each saber has its own WLED Sync switch.

To add/remove sabers: add/remove a package block in `xenopixel_simple.yaml` and update the WLED dispatch lambda. ESP32 supports up to 3 simultaneous GATT client connections.

### Tools (`tools/`)

- `diagnose_ble.py` — BLE diagnostics (BlueZ version, kernel modules, bonding state)
- `parse_btsnoop.py` — HCI snoop log parser for protocol analysis
- `test_saber.py` — General saber test tool (scan, read, power, color, brightness)

### Testing

**Python tests (`tests/`)** — pytest with coverage. Tests the BLE protocol encoder/decoder (`test_protocol.py`) and constants (`test_const.py`). CI enforces 80% minimum coverage.

**C++ tests (`tests/cpp/`)** — GoogleTest-based host tests for the ESPHome `XenopixelLight` component. No ESP32 hardware required — uses mock stubs for all ESPHome and ESP-IDF types.

- `mocks/esphome_mock.h` — Single header providing test doubles for `Component`, `LightOutput`, `BLEClient`, `GlobalsComponent`, and ESP-IDF BLE functions. A global `g_ble_writes()` vector captures all BLE write calls for assertion. A controllable `millis()` allows testing debounce logic.
- `mocks/esphome/` — Stub headers that shadow real ESPHome `#include` paths so `xenopixel_light.h` compiles unmodified.
- `test_xenopixel_light.cpp` — 31 test cases covering: traits declaration, guard conditions (syncing/authorization), power on/off commands, brightness, color with debounce, redundancy skipping, RGB recovery from brightness division, float clamping, handle caching/reset, null safety, and WLED sync (packet validation, brightness mapping, power off on zero brightness, authorization-only guard, syncing bypass, write_state blocking).
- `CMakeLists.txt` — Fetches GoogleTest v1.15.2 via `FetchContent`. Builds with `--coverage` flags for gcov/lcov instrumentation. Defines `UNIT_TEST` to guard any platform-specific code from host builds.

**CI pipeline (`.github/workflows/tests.yaml`)** — Three jobs:
1. `tests` — Python tests with coverage → uploads `coverage.xml` artifact
2. `cpp-tests` — C++ build/test with lcov → uploads `coverage.info` artifact
3. `coverage-upload` — Downloads both artifacts, uploads to Codacy as partial reports, then finalizes

### Key Technical Constraint

Linux BlueZ blocks CCCD descriptor writes with "NotPermitted" for this device. The ESP32's BLE stack handles this correctly. See `docs/BLE_COMPATIBILITY.md` for the full analysis.

## Key Reference Documents

- **`PROTOCOL.md`** — Complete BLE protocol specification with all known commands and capture sessions
- **`docs/BLE_COMPATIBILITY.md`** — Why Linux BlueZ fails and the ESP32 solution
- **`docs/DEVELOPMENT_PLAN.md`** — Development roadmap
- **`references/Agent_review.md`** — Deep technical analysis of the Xenopixel BLE protocol
