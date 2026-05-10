# Smart Light Controller 💡

[![GitHub release](https://img.shields.io/github/v/release/dr-nico-f/smart-light-controller)](https://github.com/dr-nico-f/smart-light-controller/releases) [![CI](https://github.com/dr-nico-f/smart-light-controller/actions/workflows/ci.yml/badge.svg)](https://github.com/dr-nico-f/smart-light-controller/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Local-First Tuya Smart Bulb Control** | [**Live Demo**](https://dr-nico-f.github.io/smart-light-controller/)

CLI, Python library, and HTTP API for controlling Tuya-based RGBCW smart bulbs directly over the LAN — no cloud round-trip required. Includes named colour presets, smooth transitions, scene orchestration, device discovery, network diagnostics, and an automation engine.

Built with **Python 3.11+** and **TinyTuya**.

---

## 💡 Motivation

Most smart-light ecosystems push everything through a cloud service, adding latency and a single point of failure. This project takes the opposite approach: talk to the bulbs directly over the local network using the Tuya protocol, falling back to cloud only for initial device discovery and stale-IP refresh.

What started as a quick script to toggle a desk lamp grew into a full service layer with a CLI, HTTP API, scene definitions, device registry, automatic fallback/retry, transition effects, and network diagnostics — designed to be extended with menu-bar controls, webhook automations, or anything else that can call a Python function.

---

## 🚀 Features

- **Local LAN control** — on/off, brightness, white mode, HSV colour, raw DPS commands
- **25 named colour presets** — `sunset-orange`, `ocean-blue`, `candlelight`, `lavender`, and more
- **Smooth transitions** — `fade` to a brightness over N seconds, `breathe` with configurable cycles
- **Scene engine** — declarative multi-device scenes defined in JSON (`movie-time`, `party`, etc.)
- **Device registry** — slug/name/room/group resolution; target `all`, a room, a group, or a single bulb
- **Auto-discovery** — runs the TinyTuya wizard non-interactively to import new bulbs
- **Refresh & fallback** — if a command fails due to a stale IP, the service rescans the LAN and retries
- **Network diagnostics** — TCP probe, subnet comparison, VPN detection, SSID check, and human-friendly likely-cause hints
- **Web dashboard** — glassmorphism dark-themed control panel with device cards, colour presets, scenes, transitions, and keyboard shortcuts ([live demo](https://dr-nico-f.github.io/smart-light-controller/))
- **HTTP API** — full-featured FastAPI server for integration with Home Assistant, iOS Shortcuts, etc.
- **Automation primitives** — trigger-to-scene rules ready for future menu-bar or webhook integrations
- **Clean CLI** — every operation available as a `smart-lights` subcommand with JSON output

---

## ⚙️ Setup

### 1. Clone and install

```bash
git clone https://github.com/dr-nico-f/smart-light-controller.git
cd smart-light-controller
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"        # core + test dependencies
pip install -e ".[api]"        # adds HTTP API server (FastAPI + uvicorn)
```

### 2. Configuration

Copy the example configs and fill in your credentials:

```bash
cp -r config.example/ config/
```

Edit `config/cloud.json` with your Tuya IoT Platform credentials, then run discovery:

```bash
smart-lights discover --max-time 8
```

This populates `config/devices.json` automatically. Scene definitions go in `config/scenes.json` (see `config.example/` for the format).

All config files are gitignored — they contain device keys and local IPs.

---

## 🧠 Usage

### Device control

```bash
smart-lights devices                          # list all configured bulbs
smart-lights on living-room                   # turn on a room
smart-lights off all                          # everything off
smart-lights dim living-room 40               # set brightness (0-100)
smart-lights white living-room --brightness 80 --colourtemp 50
```

### Colour (named presets or raw HSV)

```bash
smart-lights colours                          # list all 25 presets
smart-lights color living-room sunset-orange  # use a named preset
smart-lights color living-room --h 240 --s 800 --v 600  # raw HSV
```

### Transitions

```bash
smart-lights fade living-room 80 --from 0 --duration 5   # 5-second fade
smart-lights breathe living-room --cycles 4 --duration 3  # breathing pulse
```

### Scenes

```bash
smart-lights scenes           # list available scenes
smart-lights scene movie-time # apply a scene
```

### Discovery and diagnostics

```bash
smart-lights discover --max-time 8
smart-lights refresh
smart-lights diagnose all --timeout 2
smart-lights status all
```

### HTTP API & Web Dashboard

```bash
smart-lights serve --port 8000
```

Open `http://localhost:8000` for the **web control dashboard** — a glassmorphism dark-themed control panel featuring:
- Device cards grouped by room with on/off toggles and brightness sliders
- 25 colour presets + custom colour picker with per-device targeting
- Scene buttons with thematic colour feedback on device cards
- Fade and breathe transition controls
- Keyboard shortcuts (`1`–`9` toggle, `Esc` all-off, `F` fade, `B` breathe)

Try the [**live demo**](https://dr-nico-f.github.io/smart-light-controller/) (runs in demo mode with mock data).

Interactive API docs are at `http://localhost:8000/docs`. You can also use the API directly:

```bash
curl http://localhost:8000/devices
curl -X POST http://localhost:8000/devices/living-room/on
curl -X POST http://localhost:8000/devices/living-room/colour \
  -H "Content-Type: application/json" \
  -d '{"preset": "ocean-blue"}'
curl -X POST http://localhost:8000/scenes/movie-time
```

---

## 🧱 Project Structure

```
src/smart_lights/
  cli.py              → argparse CLI (devices, status, on, off, dim, color, fade, breathe, serve, …)
  service.py          → application service layer with auto-retry and fallback
  tuya_client.py      → TinyTuya local and cloud API wrappers
  bulbs.py            → high-level single-bulb operations
  models.py           → typed dataclasses (DeviceConfig, CloudConfig, SceneConfig, CommandResult, …)
  config.py           → JSON config loading and path resolution
  registry.py         → device inventory with slug/name/room/group resolution
  scenes.py           → scene loading and lookup
  colours.py          → 25 named colour presets with HSV values
  transitions.py      → fade and breathe transition effects
  automation.py       → trigger-to-scene automation engine
  api.py              → FastAPI HTTP server
  static/index.html   → web control dashboard (dark theme, no build step)
  py.typed            → PEP 561 type-checking marker

config.example/        → sanitized example configs (copy to config/ and edit)
tests/                 → 53 pytest tests with fixture-based isolation
.github/workflows/     → CI: pytest + mypy across Python 3.11–3.13
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  CLI  (cli.py)              HTTP API  (api.py)          │
│  argparse → JSON stdout     FastAPI → JSON responses    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  Service Layer  (service.py)                            │
│  coordinates registry, scenes, local/cloud clients      │
│  auto-retry with metadata refresh on connectivity error │
└───┬──────────────┬──────────────┬───────────────────────┘
    │              │              │
┌───▼───┐   ┌─────▼─────┐   ┌───▼────────────────────┐
│ Device │   │  Scene    │   │  Automation Engine      │
│Registry│   │  Library  │   │  trigger → scene runner │
└───┬────┘   └───────────┘   └─────────────────────────┘
    │
┌───▼──────────────────────────────────────────────────────┐
│  Bulb Controller  (bulbs.py)                             │
│  + Colour Presets  (colours.py)                          │
│  + Transitions  (transitions.py)                         │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Tuya Clients  (tuya_client.py)                          │
│  LocalTuyaClient: LAN control, scan, probe, wizard       │
│  CloudTuyaClient: metadata fetch, status, functions       │
└──────────────────────┬───────────────────────────────────┘
                       │
               ┌───────▼───────┐
               │  TinyTuya     │
               │  (LAN + Cloud)│
               └───────────────┘
```

**Local-first by design.** Every command flows through `LocalTuyaClient`, which opens a direct TCP connection to the bulb on port 6668. Cloud credentials are only used for initial device discovery (the TinyTuya wizard needs them to fetch device keys) and fallback IP refresh when a bulb becomes unreachable. The service layer automatically detects connectivity errors (TinyTuya codes 901–904), rescans the network, and retries — so stale DHCP leases are handled transparently.

---

## 🛠️ Tech Stack

| **Language** | Python 3.11+ |
| --- | --- |
| **Protocol** | Tuya local protocol v3.3 via TinyTuya |
| **HTTP API** | FastAPI + Uvicorn |
| **Packaging** | `pyproject.toml` + setuptools |
| **Config** | JSON files in `config/` (gitignored) |
| **Testing** | pytest (53 tests, fixture-isolated) |
| **CI** | GitHub Actions (Python 3.11, 3.12, 3.13) |
| **Type checking** | mypy with `py.typed` marker |

---

## 🧪 Testing

```bash
pip install -e ".[dev,api]"
pytest
```

The test suite covers config loading, device registry resolution and merge logic, scene retrieval, service layer operations with fallback behaviour, colour preset resolution, transition interpolation, and HTTP API endpoints — **53 tests** across 7 modules, all fixture-based and runnable after a clean clone.

---

## 📡 API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/devices` | List all configured devices |
| `GET` | `/scenes` | List available scene names |
| `GET` | `/colours` | List colour presets |
| `GET` | `/devices/{target}/status` | Get device/group status |
| `POST` | `/devices/{target}/on` | Turn on |
| `POST` | `/devices/{target}/off` | Turn off |
| `POST` | `/devices/{target}/brightness` | Set brightness |
| `POST` | `/devices/{target}/white` | Set white mode |
| `POST` | `/devices/{target}/colour` | Set colour (preset or HSV) |
| `POST` | `/devices/{target}/fade` | Smooth brightness fade |
| `POST` | `/devices/{target}/breathe` | Breathing pulse effect |
| `POST` | `/scenes/{name}` | Apply a scene |
| `GET` | `/diagnose/{target}` | Run network diagnostics |

---

## 🛠️ Development Notes

- Requires **Python 3.11+** (developed on 3.12)
- Packaging via `pyproject.toml`; install with `pip install -e ".[dev,api]"`
- Uses `tinytuya` as the sole runtime dependency; `fastapi` + `uvicorn` for the optional HTTP API
- Config files are gitignored; see `config.example/` for the expected format
- All CLI output is JSON for easy scripting and composition
- Structured logging via Python's `logging` module at key service layer points

---

## 📜 License

MIT © 2025–2026 — Created by Nico
