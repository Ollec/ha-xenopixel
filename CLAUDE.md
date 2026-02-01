# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESPHome proxy for controlling Xenopixel V3 lightsabers via BLE. Uses an ESP32 as a BLE-to-WiFi bridge to work around Linux BlueZ CCCD compatibility issues.

- **`esphome/`** — ESP32 BLE-to-WiFi proxy configs (the working product)
- **`src/xenopixel_ble/`** — Python BLE protocol library (encoder/decoder, constants, state management)

## Commands

```bash
# Install dependencies
uv sync --group dev

# Run Python tests
uv run pytest

# Run Python tests with coverage (CI enforces 80% minimum)
uv run pytest --cov=src/xenopixel_ble --cov-report=term-missing --cov-fail-under=80

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
uv run mypy src/xenopixel_ble

# Code complexity (CI thresholds: CCN 15, length 100, args 6)
uv run lizard src/xenopixel_ble/ -C 15 -L 100 -a 6 -w -i 0

# ESPHome compile (requires esphome installed via uv tool)
cd esphome && esphome compile xenopixel_1saber.yaml
cd esphome && esphome compile xenopixel_2sabers.yaml

# ESPHome compile + flash
cd esphome && esphome run xenopixel_1saber.yaml   # single saber
cd esphome && esphome run xenopixel_2sabers.yaml   # dual sabers
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

### Python BLE Protocol Library (`src/xenopixel_ble/`)

- `protocol.py` — Encoder/decoder for all BLE commands and responses. `XenopixelProtocol` has static methods for each command. `XenopixelState` dataclass holds parsed device state.
- `const.py` — Domain, BLE UUIDs, message types, parameter names, authorization values.
- `__init__.py` — Package entry point with clean re-exports.

### ESPHome Proxy (`esphome/`)

- `xenopixel_1saber.yaml` / `xenopixel_2sabers.yaml` — Top-level configs for single or dual saber setups. Each defines substitutions (`device_name`, `friendly_name`) and includes the shared base package plus the appropriate number of saber packages. Users compile the file matching their saber count.
- `packages/base.yaml` — Shared infrastructure (ESPHome core, WiFi, API, OTA, BLE tracker, web server, captive portal). WiFi power save is disabled (`power_save_mode: NONE`) to ensure reliable UDP broadcast reception.
- `packages/saber.yaml` — Per-saber template. Contains all entities for one saber (BLE client, authorization, sensors, light, numbers, buttons, switches). Uses `${saber_id}`, `${saber_name}`, `${saber_mac}` variables for text substitution via ESPHome's `packages:` with `vars:`.
- `components/xenopixel_light/xenopixel_light.h` — Custom ESPHome `LightOutput` component. Sends separate BLE commands for power, brightness, and color (instead of ESPHome's combined RGB values). Includes redundancy checks (skips unchanged values), color debouncing (100ms), brightness recovery (divides out ESPHome's baked-in brightness), guard conditions (blocks commands while syncing or unauthorized), and WLED UDP sync support (static shared UDP socket across all instances, generation counter ensures each instance processes each packet exactly once).
- `components/xenopixel_light/light.py` — ESPHome code generation for the component. Depends on `ble_client` and `wifi`.
- `secrets.yaml` — WiFi/API credentials and saber MAC addresses (gitignored).

#### Multi-Saber Architecture

Separate top-level YAML files control how many sabers are compiled in — only real sabers get entities. Users pick the file matching their saber count at flash time:

- `xenopixel_1saber.yaml` — includes base + 1 saber package
- `xenopixel_2sabers.yaml` — includes base + 2 saber packages

Adding a 3rd saber = create `xenopixel_3sabers.yaml` with a third package include. No conditional logic or Jinja needed.

The ESPHome config uses `packages:` with `vars:` (ESPHome 2025.3.0+) for per-saber text substitution before C++ compilation:

```yaml
packages:
  base: !include packages/base.yaml
  saber1: !include
    file: packages/saber.yaml
    vars:
      saber_id: saber1
      saber_name: !secret saber1_name
      saber_mac: !secret saber1_mac
```

Entity naming: IDs use `${saber_id}_<suffix>` (e.g., `saber1_light`), names use `"${friendly_name} ${saber_name} <Entity>"` (e.g., "Xenopixel Saber 1 Blade").

WLED UDP sync is built into the component — a static shared UDP socket across all instances ensures each saber with WLED active receives packets. Each saber has its own WLED Sync switch. ESP32 supports up to 3 simultaneous GATT client connections.

#### WLED Sync — Protocol Details and Limitations

The component listens on UDP port 21324 for WLED notifier packets (byte 0 = 0, byte 2 = brightness, bytes 3-5 = RGB). This is a best-effort sync:

- **Solid colors** sync reliably. This is the intended use case — matching a saber to room lighting or themed scenes.
- **Animated effects** are approximate. WLED's notifier protocol sends the segment's primary color on change, not the per-pixel rendered output every frame. The saber receives color updates only when the effect internally cycles the primary color.
- **UDP packet loss** is inherent. The ESP32 shares one 2.4GHz radio between WiFi and BLE. Active GATT connections preempt WiFi, and UDP has no retransmission. Observed: ~10% loss with 1 saber, ~15-20% with 2.
- **Keepalive is paused** during WLED sync (checked via `id(${saber_id}_wled_sync).state` in the keepalive lambda) to prevent the keepalive from overwriting WLED brightness with a stale cached value.
- **3AB1 brightness sync** — the 3AB1 notification handler parses brightness confirmations and updates the ESPHome light entity, keeping the HA UI accurate and preventing stale values if WLED is later disabled.

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
