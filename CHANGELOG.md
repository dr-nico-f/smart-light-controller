# Changelog

## 1.0.0 (2026-05-10)

Initial release.

### Features

- **Local LAN control** — on/off, brightness, white mode, HSV colour, raw DPS commands
- **Scene engine** — declarative multi-device scenes defined in JSON
- **Device registry** — slug/name/room/group resolution with flexible targeting
- **Auto-discovery** — non-interactive TinyTuya wizard integration
- **Refresh & fallback** — automatic rescan and retry on connectivity errors
- **Network diagnostics** — TCP probe, subnet check, VPN detection, likely-cause hints
- **Named colour presets** — 25 built-in colours (`sunset-orange`, `ocean-blue`, `candlelight`, etc.)
- **Transition effects** — `fade` and `breathe` commands with configurable duration
- **HTTP API** — FastAPI server with full endpoint coverage (`smart-lights serve`)
- **Automation primitives** — trigger-to-scene rule engine for future integrations
- **CLI** — complete command set with JSON output, error handling, and colour listing
- **CI** — GitHub Actions workflow with pytest + mypy across Python 3.11–3.13
