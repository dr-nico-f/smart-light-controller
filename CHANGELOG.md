# Changelog

## 1.1.0 (2026-05-10)

### Added

- **Web control dashboard** — dark-themed single-page UI served at `localhost:8000` with no build step required
  - Device cards grouped by room with on/off toggles and brightness sliders
  - 25 colour preset swatches with hover tooltips and glow effects
  - Custom colour picker (native input with rainbow ring)
  - Inline target selector for applying colours to specific devices
  - Scene buttons with thematic visual feedback (colour strips on device cards)
  - Transition controls (fade and breathe) with target/brightness/duration fields
  - Keyboard shortcuts: `1`–`9` toggle devices, `Esc` all-off, `F` fade, `B` breathe
  - Live "last refreshed" timestamp in the status pill
  - Demo mode with mock data when API is unreachable
- **GitHub Pages deployment** — live interactive demo at the repository's Pages URL
- **Glassmorphism UI** with animated background orbs, card hover effects, staggered entrance animations, and toast notifications
- **SVG favicon** (inline purple lightbulb)

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
