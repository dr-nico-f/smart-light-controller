"""Command-line interface for the smart lights toolkit."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from smart_lights.service import SmartLightsService


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(prog="smart-lights", description="Control Tuya smart lights.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("devices", help="List configured devices")
    subparsers.add_parser("scenes", help="List configured scenes")
    subparsers.add_parser("colours", help="List available colour presets")
    subparsers.add_parser("refresh", help="Refresh device IPs from scan/cloud")

    diagnose_parser = subparsers.add_parser("diagnose", help="Inspect local and cloud reachability for bulbs")
    diagnose_parser.add_argument("target", nargs="?", default="all")
    diagnose_parser.add_argument("--timeout", type=float, default=1.5)

    discover_parser = subparsers.add_parser("discover", help="Run TinyTuya wizard discovery and import bulbs")
    discover_parser.add_argument("--max-time", type=int, default=5)
    discover_parser.add_argument("--no-poll", action="store_true")
    discover_parser.add_argument("--no-force-scan", action="store_true")

    status_parser = subparsers.add_parser("status", help="Get device status")
    status_parser.add_argument("target", nargs="?", default="all")

    on_parser = subparsers.add_parser("on", help="Turn a target on")
    on_parser.add_argument("target")

    off_parser = subparsers.add_parser("off", help="Turn a target off")
    off_parser.add_argument("target")

    dim_parser = subparsers.add_parser("dim", help="Set brightness percentage")
    dim_parser.add_argument("target")
    dim_parser.add_argument("brightness", type=int)

    white_parser = subparsers.add_parser("white", help="Set white mode")
    white_parser.add_argument("target")
    white_parser.add_argument("--brightness", type=int, default=None)
    white_parser.add_argument("--colourtemp", type=int, default=None)

    color_parser = subparsers.add_parser("color", help="Set colour by name or HSV")
    color_parser.add_argument("target")
    color_parser.add_argument("colour", nargs="?", default=None, help="Named colour preset")
    color_parser.add_argument("--h", type=int, default=None, help="Hue (0-360)")
    color_parser.add_argument("--s", type=int, default=None, help="Saturation (0-1000)")
    color_parser.add_argument("--v", type=int, default=None, help="Value (0-1000)")

    mode_parser = subparsers.add_parser("mode", help="Set a raw mode value")
    mode_parser.add_argument("target")
    mode_parser.add_argument("mode")

    scene_parser = subparsers.add_parser("scene", help="Apply a configured scene")
    scene_parser.add_argument("name")

    fade_parser = subparsers.add_parser("fade", help="Smoothly fade brightness over time")
    fade_parser.add_argument("target")
    fade_parser.add_argument("brightness", type=int, help="Target brightness (0-100)")
    fade_parser.add_argument("--from", type=int, default=None, dest="start", help="Starting brightness")
    fade_parser.add_argument("--duration", type=float, default=3.0, help="Transition seconds")
    fade_parser.add_argument("--steps", type=int, default=20, help="Number of interpolation steps")

    breathe_parser = subparsers.add_parser("breathe", help="Pulse brightness in a breathing pattern")
    breathe_parser.add_argument("target")
    breathe_parser.add_argument("--low", type=int, default=10, help="Minimum brightness")
    breathe_parser.add_argument("--high", type=int, default=100, help="Maximum brightness")
    breathe_parser.add_argument("--cycles", type=int, default=3, help="Number of breath cycles")
    breathe_parser.add_argument("--duration", type=float, default=4.0, help="Seconds per cycle")

    raw_parser = subparsers.add_parser("raw", help="Send a raw DPS value")
    raw_parser.add_argument("target")
    raw_parser.add_argument("dps", type=int)
    raw_parser.add_argument("value")

    serve_parser = subparsers.add_parser("serve", help="Start the HTTP API server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port")

    return parser


def parse_raw_value(value: str) -> Any:
    """Parse a raw command value as JSON when possible."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def print_results(results: list[Any]) -> None:
    """Pretty print command results."""
    for result in results:
        print(
            json.dumps(
                {
                    "target": result.target,
                    "success": result.success,
                    "transport": result.transport,
                    "response": result.response,
                },
                indent=2,
                sort_keys=True,
            )
        )


def main() -> int:
    """Entry point for the smart lights CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "colours":
        from smart_lights.colours import list_presets
        for preset in list_presets():
            print(f"{preset.name:<16} H={preset.hue:<4} S={preset.saturation:<5} V={preset.value}")
        return 0

    if args.command == "serve":
        return _serve(args)

    try:
        service = SmartLightsService.from_config()
    except FileNotFoundError as exc:
        print(f"error: config file not found: {exc.filename or exc}", file=sys.stderr)
        print("hint: run 'smart-lights discover' or see README for config setup", file=sys.stderr)
        return 1

    try:
        return _dispatch(args, service)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _serve(args: argparse.Namespace) -> int:
    """Start the HTTP API server."""
    try:
        import uvicorn
    except ImportError:
        print("error: install the 'api' extra: pip install -e '.[api]'", file=sys.stderr)
        return 1
    from smart_lights.api import app  # noqa: F401
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _dispatch(args: argparse.Namespace, service: SmartLightsService) -> int:
    """Route a parsed CLI command to the appropriate service method."""
    if args.command == "devices":
        for device in service.list_devices():
            print(f"{device.slug}\t{device.name}\t{device.ip_address}\t{device.room or '-'}")
        return 0

    if args.command == "scenes":
        for scene_name in service.list_scene_names():
            print(scene_name)
        return 0

    if args.command == "refresh":
        print(json.dumps(service.refresh_discovery(), indent=2, sort_keys=True))
        return 0

    if args.command == "diagnose":
        print(json.dumps(service.diagnose(args.target, timeout=args.timeout), indent=2, sort_keys=True))
        return 0

    if args.command == "discover":
        print(
            json.dumps(
                service.discover_with_wizard(
                    retries=args.max_time,
                    forcescan=not args.no_force_scan,
                    skip_poll=args.no_poll,
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "status":
        print_results(service.status(args.target))
        return 0

    if args.command == "on":
        print_results(service.turn_on(args.target))
        return 0

    if args.command == "off":
        print_results(service.turn_off(args.target))
        return 0

    if args.command == "dim":
        print_results(service.set_brightness(args.target, args.brightness))
        return 0

    if args.command == "white":
        print_results(service.set_white(args.target, brightness=args.brightness, colourtemp=args.colourtemp))
        return 0

    if args.command == "color":
        return _handle_colour(args, service)

    if args.command == "mode":
        print_results(service.set_mode(args.target, args.mode))
        return 0

    if args.command == "scene":
        print_results(service.apply_scene(args.name))
        return 0

    if args.command == "fade":
        return _handle_fade(args, service)

    if args.command == "breathe":
        return _handle_breathe(args, service)

    if args.command == "raw":
        print_results(service.set_raw_dps(args.target, args.dps, parse_raw_value(args.value)))
        return 0

    return 2


def _handle_colour(args: argparse.Namespace, service: SmartLightsService) -> int:
    """Handle the color command -- named preset or raw HSV."""
    if args.colour:
        from smart_lights.colours import resolve_colour
        preset = resolve_colour(args.colour)
        print_results(service.set_colour(args.target, preset.hue, preset.saturation, preset.value))
    elif args.h is not None and args.s is not None and args.v is not None:
        print_results(service.set_colour(args.target, args.h, args.s, args.v))
    else:
        print("error: provide a colour name or --h, --s, --v values", file=sys.stderr)
        return 1
    return 0


def _handle_fade(args: argparse.Namespace, service: SmartLightsService) -> int:
    """Handle the fade command."""
    from smart_lights.transitions import fade_brightness
    devices = service.registry.resolve(args.target)
    start = args.start if args.start is not None else 0
    results = []
    for device in devices:
        result = fade_brightness(
            device, service.local_client,
            start=start, end=args.brightness,
            duration=args.duration, steps=args.steps,
        )
        results.append({"target": device.slug, "result": result})
    print(json.dumps(results, indent=2))
    return 0


def _handle_breathe(args: argparse.Namespace, service: SmartLightsService) -> int:
    """Handle the breathe command."""
    from smart_lights.transitions import breathe
    devices = service.registry.resolve(args.target)
    results = []
    for device in devices:
        result = breathe(
            device, service.local_client,
            low=args.low, high=args.high,
            cycle_duration=args.duration, cycles=args.cycles,
        )
        results.append({"target": device.slug, "result": result})
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
