"""Thin wrappers around TinyTuya local and cloud APIs."""

from __future__ import annotations

import colorsys
import importlib
import json
from pathlib import Path
import socket
import subprocess
from typing import Any

import tinytuya
from tinytuya import wizard as tinytuya_wizard

from smart_lights.models import CloudConfig, DeviceConfig


CONNECTIVITY_ERROR_CODES = {"901", "902", "903", "904"}
DEFAULT_TUYA_PORT = 6668


def response_error_code(response: dict[str, Any] | None) -> str | None:
    """Extract a TinyTuya error code from a response, if present."""
    if not response:
        return None
    value = response.get("Err")
    return str(value) if value is not None else None


def is_success_response(response: dict[str, Any] | None) -> bool:
    """Return True when a TinyTuya response does not report an error."""
    return bool(response) and "Err" not in response


def is_connectivity_error(response: dict[str, Any] | None) -> bool:
    """Return True when the response indicates a connection issue."""
    return response_error_code(response) in CONNECTIVITY_ERROR_CODES


class LocalTuyaClient:
    """Executes local LAN commands against Tuya bulbs."""

    @staticmethod
    def _run_command(*args: str) -> str | None:
        """Run a system command and return trimmed stdout when available."""
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                check=False,
                text=True,
            )
        except OSError:
            return None
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        return output or None

    def _get_default_route_info(self) -> dict[str, str | None]:
        """Return the default gateway and interface, when detectable."""
        output = self._run_command("route", "-n", "get", "default")
        info: dict[str, str | None] = {"gateway": None, "interface": None}
        if not output:
            return info
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("gateway:"):
                info["gateway"] = line.split(":", 1)[1].strip()
            elif line.startswith("interface:"):
                info["interface"] = line.split(":", 1)[1].strip()
        return info

    def _get_wifi_ssid(self, interface: str | None) -> str | None:
        """Return the current Wi-Fi SSID for the active interface, when available."""
        if not interface:
            return None
        output = self._run_command("networksetup", "-getairportnetwork", interface)
        if not output:
            return None
        marker = "Current Wi-Fi Network:"
        if marker in output:
            return output.split(marker, 1)[1].strip() or None
        if "You are not associated with an AirPort network" in output:
            return None
        return output

    def _get_active_vpn_interfaces(self) -> list[str]:
        """Return active utun interfaces, which often indicates VPN tunneling."""
        output = self._run_command("ifconfig")
        if not output:
            return []
        interfaces: list[str] = []
        current: str | None = None
        is_up = False
        for raw_line in output.splitlines():
            if raw_line and not raw_line.startswith("\t") and ":" in raw_line:
                if current and is_up and current.startswith("utun"):
                    interfaces.append(current)
                current = raw_line.split(":", 1)[0]
                is_up = "UP" in raw_line
                continue
            if current and "status: active" in raw_line:
                is_up = True
        if current and is_up and current.startswith("utun"):
            interfaces.append(current)
        return interfaces

    def _build_device(self, device: DeviceConfig) -> tinytuya.BulbDevice:
        bulb = tinytuya.BulbDevice(
            dev_id=device.device_id,
            address=device.ip_address,
            local_key=device.local_key,
        )
        bulb.set_version(float(device.version))
        return bulb

    def status(self, device: DeviceConfig) -> dict[str, Any]:
        """Fetch the current device status via LAN."""
        return self._build_device(device).status()

    def turn_on(self, device: DeviceConfig) -> dict[str, Any]:
        """Power the device on."""
        return self._build_device(device).set_status(True, switch=device.dps.switch)

    def turn_off(self, device: DeviceConfig) -> dict[str, Any]:
        """Power the device off."""
        return self._build_device(device).set_status(False, switch=device.dps.switch)

    def set_mode(self, device: DeviceConfig, mode: str) -> dict[str, Any]:
        """Change the bulb mode."""
        return self._build_device(device).set_mode(mode)

    def set_brightness(self, device: DeviceConfig, brightness: int) -> dict[str, Any]:
        """Set brightness on the bulb using TinyTuya's normalized API."""
        return self._build_device(device).set_brightness_percentage(brightness)

    def set_white(
        self,
        device: DeviceConfig,
        brightness: int | None = None,
        colourtemp: int | None = None,
    ) -> dict[str, Any]:
        """Put the bulb in white mode and optionally set white parameters."""
        bulb = self._build_device(device)
        bulb.set_mode("white")
        if brightness is None:
            brightness = 100
        if colourtemp is None:
            colourtemp = 0
        return bulb.set_white_percentage(brightness=brightness, colourtemp=colourtemp)

    def set_colour_hsv(
        self,
        device: DeviceConfig,
        hue: int,
        saturation: int,
        value: int,
    ) -> dict[str, Any]:
        """Set bulb colour using normalized HSV inputs."""
        red, green, blue = colorsys.hsv_to_rgb(hue / 360.0, saturation / 1000.0, value / 1000.0)
        bulb = self._build_device(device)
        bulb.set_mode("colour")
        return bulb.set_colour(
            int(red * 255),
            int(green * 255),
            int(blue * 255),
        )

    def set_scene(self, device: DeviceConfig, scene: int | str) -> dict[str, Any]:
        """Apply a TinyTuya scene number or raw scene identifier."""
        return self._build_device(device).set_scene(scene)

    def set_value(self, device: DeviceConfig, dps: int, value: Any) -> dict[str, Any]:
        """Send a raw DPS value for precise device control."""
        return self._build_device(device).set_value(dps, value)

    def scan_devices(self, max_seconds: int = 5) -> list[dict[str, Any]]:
        """Scan the LAN for Tuya devices and normalize the results."""
        try:
            scanned = tinytuya.deviceScan(
                verbose=False,
                maxretry=max_seconds,
                color=False,
                poll=False,
                forcescan=True,
            )
        except Exception:
            return []
        results: list[dict[str, Any]] = []
        for ip_address, payload in scanned.items():
            device_ip = payload.get("ip", ip_address)
            results.append(
                {
                    "device_id": payload.get("gwId") or payload.get("id"),
                    "ip_address": device_ip,
                    "version": str(payload.get("version") or payload.get("ver") or "3.3"),
                    "product_key": payload.get("productKey"),
                }
            )
        return results

    def get_local_network_info(self) -> dict[str, Any]:
        """Return best-effort information about the current local network path."""
        local_ip = None
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("8.8.8.8", 80))
                local_ip = probe.getsockname()[0]
        except OSError:
            pass
        route_info = self._get_default_route_info()
        return {
            "local_ip": local_ip,
            "tuya_port": DEFAULT_TUYA_PORT,
            "hostname": socket.gethostname(),
            "default_gateway": route_info["gateway"],
            "default_interface": route_info["interface"],
            "wifi_ssid": self._get_wifi_ssid(route_info["interface"]),
            "active_vpn_interfaces": self._get_active_vpn_interfaces(),
        }

    def probe_address(
        self,
        ip_address: str,
        *,
        port: int = DEFAULT_TUYA_PORT,
        timeout: float = 1.5,
    ) -> dict[str, Any]:
        """Check whether a TCP connection can be opened to the target device."""
        try:
            with socket.create_connection((ip_address, port), timeout=timeout):
                return {"reachable": True, "error": None, "port": port}
        except OSError as exc:
            return {
                "reachable": False,
                "error": str(exc),
                "errno": exc.errno,
                "port": port,
            }

    def run_wizard(
        self,
        cloud_config: CloudConfig,
        *,
        credentials_file: str | Path,
        device_file: str | Path,
        snapshot_file: str | Path,
        raw_file: str | Path,
        retries: int | None = 5,
        forcescan: bool = True,
        skip_poll: bool = False,
    ) -> list[dict[str, Any]]:
        """Run TinyTuya's setup wizard non-interactively and return discovered devices."""
        credentials_path = Path(credentials_file)
        device_path = Path(device_file)
        snapshot_path = Path(snapshot_file)
        raw_path = Path(raw_file)
        for path in (credentials_path, device_path, snapshot_path, raw_path):
            path.parent.mkdir(parents=True, exist_ok=True)

        credentials = {
            "file": str(credentials_path),
            "apiKey": cloud_config.api_key,
            "apiSecret": cloud_config.api_secret,
            "apiRegion": cloud_config.api_region,
            "apiDeviceID": cloud_config.api_device_id,
        }

        old_files = (
            tinytuya_wizard.CONFIGFILE,
            tinytuya_wizard.DEVICEFILE,
            tinytuya_wizard.SNAPSHOTFILE,
            tinytuya_wizard.RAWFILE,
        )
        try:
            if not hasattr(tinytuya, "scanner"):
                tinytuya.scanner = importlib.import_module("tinytuya.scanner")
            tinytuya_wizard.CONFIGFILE = str(credentials_path)
            tinytuya_wizard.DEVICEFILE = str(device_path)
            tinytuya_wizard.SNAPSHOTFILE = str(snapshot_path)
            tinytuya_wizard.RAWFILE = str(raw_path)
            tinytuya_wizard.wizard(
                color=False,
                retries=retries,
                forcescan=forcescan,
                nocloud=False,
                assume_yes=True,
                discover=True,
                credentials=credentials,
                skip_poll=skip_poll,
            )
        finally:
            (
                tinytuya_wizard.CONFIGFILE,
                tinytuya_wizard.DEVICEFILE,
                tinytuya_wizard.SNAPSHOTFILE,
                tinytuya_wizard.RAWFILE,
            ) = old_files

        if not device_path.exists():
            return []
        try:
            with device_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return []
        return payload if isinstance(payload, list) else []


class CloudTuyaClient:
    """Small wrapper around TinyTuya cloud access."""

    def __init__(self, config: CloudConfig | None) -> None:
        self._config = config
        self._client: tinytuya.Cloud | None = None

    @property
    def is_enabled(self) -> bool:
        """Return True when cloud credentials are configured."""
        return self._config is not None

    @property
    def config(self) -> CloudConfig | None:
        """Return the configured cloud credentials."""
        return self._config

    def _get_client(self) -> tinytuya.Cloud:
        if self._config is None:
            raise RuntimeError("Cloud client is not configured")
        if self._client is None:
            self._client = tinytuya.Cloud(
                apiRegion=self._config.api_region,
                apiKey=self._config.api_key,
                apiSecret=self._config.api_secret,
                apiDeviceID=self._config.api_device_id,
            )
        return self._client

    def get_devices(self) -> list[dict[str, Any]]:
        """Fetch devices from the Tuya cloud."""
        try:
            result = self._get_client().getdevices()
        except Exception:
            return []
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        if isinstance(result, list):
            return result
        return []

    def get_status(self, device_id: str) -> dict[str, Any]:
        """Fetch device status from the Tuya cloud."""
        try:
            return self._get_client().getstatus(device_id)
        except Exception as exc:
            return {"Err": "cloud", "Error": str(exc)}

    def get_functions(self, device_id: str) -> dict[str, Any]:
        """Fetch device capabilities from the Tuya cloud."""
        try:
            return self._get_client().getfunctions(device_id)
        except Exception as exc:
            return {"Err": "cloud", "Error": str(exc)}
