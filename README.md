# Smart Light Controller 💡

**Local-First Tuya Smart Bulb Control**

CLI and Python library for controlling Tuya-based RGBCW smart bulbs directly over the LAN — no cloud round-trip required. Scenes, device discovery, network diagnostics, and an automation engine are included out of the box.

Built with **Python 3.11+** and **TinyTuya**.

---

## 💡 Motivation

Most smart-light ecosystems push everything through a cloud service, adding latency and a single point of failure. This project takes the opposite approach: talk to the bulbs directly over the local network using the Tuya protocol, falling back to cloud only for initial device discovery and stale-IP refresh.

What started as a quick script to toggle a desk lamp grew into a full service layer with a CLI, scene definitions, device registry, automatic fallback/retry, and network diagnostics — designed to be extended with menu-bar controls, webhook automations, or anything else that can call a Python function.

---

## 🚀 Features

- **Local LAN control** — on/off, brightness, white mode, HSV colour, raw DPS commands
- **Scene engine** — declarative multi-device scenes defined in JSON (`movie-time`, `reading`, etc.)
- **Device registry** — slug/name/room/group resolution; target `all`, a room, a group, or a single bulb
- **Auto-discovery** — runs the TinyTuya wizard non-interactively to import new bulbs
- **Refresh & fallback** — if a command fails due to a stale IP, the service rescans the LAN (or cloud) and retries
- **Network diagnostics** — TCP probe, subnet comparison, VPN detection, SSID check, and human-friendly likely-cause hints
- **Automation primitives** — trigger-to-scene rules ready for future menu-bar or webhook integrations
- **Clean CLI** — every operation is available as a `smart-lights` subcommand with JSON output

---

## 🧱 Project Structure

```
src/smart_lights/
  cli.py              → argparse CLI (devices, status, on, off, dim, white, color, scene, …)
  service.py          → application service layer shared by CLI, automations, and future UIs
  tuya_client.py      → thin wrappers around TinyTuya local and cloud APIs
  bulbs.py            → high-level single-bulb operations
  models.py           → typed dataclasses (DeviceConfig, CloudConfig, SceneConfig, CommandResult, …)
  config.py           → JSON config loading and path resolution
  registry.py         → device inventory with slug/name/room/group resolution and merge logic
  scenes.py           → scene loading and lookup
  automation.py       → trigger-to-scene automation engine

config/                (gitignored — contains local secrets)
  cloud.json           → Tuya cloud API credentials
  devices.json         → physical bulb inventory (IDs, keys, IPs)
  scenes.json          → reusable scene definitions
  automations.json     → trigger-to-scene automation rules

tests/
  test_config.py       → config loading / path resolution
  test_registry.py     → device lookup, slug normalization, merge logic
  test_scenes.py       → scene loading and retrieval
  test_service.py      → service layer operations and fallback behaviour
```

---

## ⚙️ Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/dr-nico-f/smart-light-controller.git
cd smart-light-controller
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configuration

Create `config/cloud.json` with your Tuya IoT Platform credentials:

```json
{
  "apiKey": "your-api-key",
  "apiSecret": "your-api-secret",
  "apiRegion": "us",
  "apiDeviceID": "scan"
}
```

Run discovery to populate `config/devices.json`:

```bash
smart-lights discover --max-time 8
```

Scene definitions go in `config/scenes.json`:

```json
{
  "scenes": [
    {
      "name": "movie-time",
      "description": "Dim warm lights for movie watching",
      "actions": [
        { "target": "living-room", "mode": "white", "brightness": 20, "colourtemp": 10 }
      ]
    }
  ]
}
```

_(All config files are gitignored — they contain device keys and local IPs.)_

---

## 🧠 Usage

### List devices and scenes

```bash
smart-lights devices
smart-lights scenes
```

### Control individual bulbs or groups

```bash
smart-lights on living-room-top
smart-lights off all
smart-lights dim living-room 40
smart-lights white living-room-top --brightness 80 --colourtemp 50
smart-lights color living-room-top --h 240 --s 800 --v 600
```

### Apply a scene

```bash
smart-lights scene movie-time
```

### Discovery and diagnostics

```bash
smart-lights discover --max-time 8
smart-lights refresh
smart-lights diagnose all --timeout 2
smart-lights status all
```

### Raw DPS control

```bash
smart-lights raw living-room-top 22 500
```

All commands output structured JSON, making them easy to pipe into `jq` or other tools.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│  CLI  (cli.py)                                      │
│  argparse subcommands → JSON stdout                 │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  Service Layer  (service.py)                        │
│  coordinates registry, scenes, local/cloud clients  │
│  auto-retry with metadata refresh on failure        │
└───┬──────────────┬──────────────┬───────────────────┘
    │              │              │
┌───▼───┐   ┌─────▼─────┐   ┌───▼────────────────────┐
│ Device │   │  Scene    │   │  Automation Engine      │
│Registry│   │  Library  │   │  trigger → scene runner │
└───┬────┘   └───────────┘   └─────────────────────────┘
    │
┌───▼──────────────────────────────────────────────────┐
│  Bulb Controller  (bulbs.py)                         │
│  high-level single-device operations                 │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│  Tuya Clients  (tuya_client.py)                      │
│  LocalTuyaClient: LAN control, scan, probe, wizard   │
│  CloudTuyaClient: metadata fetch, status, functions   │
└──────────────────────┬───────────────────────────────┘
                       │
               ┌───────▼───────┐
               │  TinyTuya     │
               │  (LAN + Cloud)│
               └───────────────┘
```

**Local-first by design.** Every command flows through `LocalTuyaClient`, which opens a direct TCP connection to the bulb on port 6668. Cloud credentials are only used for two things: initial device discovery (the TinyTuya wizard needs them to fetch device keys) and fallback IP refresh when a bulb becomes unreachable. The service layer automatically detects connectivity errors (TinyTuya codes 901–904), rescans the network, and retries — so stale DHCP leases are handled transparently.

---

## 🛠️ Tech Stack

| **Language** | Python 3.11+ |
| --- | --- |
| **Protocol** | Tuya local protocol v3.3 via TinyTuya |
| **Packaging** | `pyproject.toml` + setuptools |
| **Config** | JSON files in `config/` (gitignored) |
| **Testing** | pytest |

---

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest
```

The test suite covers config loading, device registry resolution and merge logic, scene retrieval, and service layer operations including fallback behaviour — **11 tests** across 4 modules.

---

## 🛠️ Development Notes

- Requires **Python 3.11+** (developed on 3.12)
- Packaging via `pyproject.toml`; install with `pip install -e ".[dev]"`
- Uses `tinytuya` as the sole runtime dependency
- Config files are gitignored; see [Setup](#%EF%B8%8F-setup) for the expected format
- All CLI output is JSON for easy scripting and composition

---

## 📜 License

MIT © 2025–2026 — Created by Nico
