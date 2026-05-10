"""Command-line interface for the smart lights toolkit."""

from __future__ import annotations

import argparse
import json
from typing import Any

from smart_lights.service import SmartLightsService


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(prog="smart-lights", description="Control Tuya smart lights.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("devices", help="List configured devices")
    subparsers.add_parser("scenes", help="List configured scenes")
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

    color_parser = subparsers.add_parser("color", help="Set HSV color")
    color_parser.add_argument("target")
    color_parser.add_argument("--h", type=int, required=True)
    color_parser.add_argument("--s", type=int, required=True)
    color_parser.add_argument("--v", type=int, required=True)

    mode_parser = subparsers.add_parser("mode", help="Set a raw mode value")
    mode_parser.add_argument("target")
    mode_parser.add_argument("mode")

    scene_parser = subparsers.add_parser("scene", help="Apply a configured scene")
    scene_parser.add_argument("name")

    raw_parser = subparsers.add_parser("raw", help="Send a raw DPS value")
    raw_parser.add_argument("target")
    raw_parser.add_argument("dps", type=int)
    raw_parser.add_argument("value")

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
    service = SmartLightsService.from_config()

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
        print_results(service.set_colour(args.target, args.h, args.s, args.v))
        return 0

    if args.command == "mode":
        print_results(service.set_mode(args.target, args.mode))
        return 0

    if args.command == "scene":
        print_results(service.apply_scene(args.name))
        return 0

    if args.command == "raw":
        print_results(service.set_raw_dps(args.target, args.dps, parse_raw_value(args.value)))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
