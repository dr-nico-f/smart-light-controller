"""Application service layer shared by CLI, automations, and future UI surfaces."""

from __future__ import annotations

import ipaddress
from pathlib import Path
from typing import Any, Callable

from smart_lights import config as config_store
from smart_lights.bulbs import TuyaBulbController
from smart_lights.models import CloudConfig, CommandResult, DeviceConfig
from smart_lights.registry import DeviceRegistry
from smart_lights.scenes import SceneLibrary
from smart_lights.tuya_client import (
    CloudTuyaClient,
    LocalTuyaClient,
    is_connectivity_error,
    is_success_response,
)


DeviceOperation = Callable[[TuyaBulbController], dict[str, Any]]


class SmartLightsService:
    """Coordinates local control, refresh, scenes, and future automation hooks."""

    def __init__(
        self,
        registry: DeviceRegistry,
        scenes: SceneLibrary,
        local_client: LocalTuyaClient | None = None,
        cloud_client: CloudTuyaClient | None = None,
    ) -> None:
        self.registry = registry
        self.scenes = scenes
        self.local_client = local_client or LocalTuyaClient()
        self.cloud_client = cloud_client or CloudTuyaClient(None)

    @classmethod
    def from_config(
        cls,
        devices_path: str | Path | None = None,
        scenes_path: str | Path | None = None,
        cloud_path: str | Path | None = None,
    ) -> "SmartLightsService":
        """Build the application service from repository config files."""
        cloud_config: CloudConfig | None = None
        try:
            cloud_config = config_store.load_cloud_config(cloud_path)
        except FileNotFoundError:
            cloud_config = None
        return cls(
            registry=DeviceRegistry.from_config(devices_path),
            scenes=SceneLibrary.from_config(scenes_path),
            cloud_client=CloudTuyaClient(cloud_config),
        )

    def list_devices(self) -> list[DeviceConfig]:
        """Return every configured device."""
        return self.registry.all_devices()

    def list_scene_names(self) -> list[str]:
        """Return available scene names."""
        return self.scenes.names()

    @staticmethod
    def _same_24_prefix(local_ip: str | None, device_ip: str) -> bool | None:
        """Return a simple same-subnet guess for common /24 home networks."""
        if not local_ip:
            return None
        try:
            local_addr = ipaddress.ip_address(local_ip)
            device_addr = ipaddress.ip_address(device_ip)
        except ValueError:
            return None
        if local_addr.version != 4 or device_addr.version != 4:
            return None
        return str(local_addr).rsplit(".", 1)[0] == str(device_addr).rsplit(".", 1)[0]

    @staticmethod
    def _diagnose_likely_causes(
        *,
        network_info: dict[str, Any],
        scanned_devices: list[dict[str, Any]],
        cloud_visible: list[dict[str, Any]],
        device_reports: list[dict[str, Any]],
    ) -> list[str]:
        """Generate human-friendly likely causes from the current diagnostics."""
        hints: list[str] = []
        reachable_count = sum(1 for report in device_reports if report["tcp_probe"]["reachable"])
        same_prefix_count = sum(1 for report in device_reports if report["same_24_prefix_as_laptop"] is True)
        route_errors = {
            report["tcp_probe"].get("errno")
            for report in device_reports
            if not report["tcp_probe"]["reachable"]
        }

        if network_info.get("active_vpn_interfaces"):
            hints.append("Active VPN/tunnel interfaces are present and may be interfering with local LAN routing.")
        if cloud_visible and not scanned_devices:
            hints.append("Cloud can see devices but local scan cannot, which usually points to LAN isolation or blocked broadcasts.")
        if reachable_count == 0 and same_prefix_count == len(device_reports) and 65 in route_errors:
            hints.append("Bulbs appear to share the same /24 subnet as the laptop, but TCP reachability still fails with 'No route to host'; that strongly suggests AP/client isolation, guest network isolation, or a segmented multi-router setup.")
        if any(report["found_by_local_scan"] and report["local_scan_ip"] != report["configured_ip"] for report in device_reports):
            hints.append("At least one configured IP differs from the latest local scan result, so stale bulb IPs may be part of the problem.")
        if not network_info.get("wifi_ssid"):
            hints.append("The active Wi-Fi SSID could not be detected automatically, so verify the laptop is on the same non-isolated SSID as the bulbs.")
        if not hints:
            hints.append("No single root cause was identified automatically; compare the active SSID/router path for the laptop and bulbs and retry when they are known to be on the same bridged LAN.")
        return hints

    def refresh_discovery(self) -> dict[str, int]:
        """Refresh device metadata from local scan and optional cloud data."""
        updates = 0
        scanned = self.local_client.scan_devices()
        updates += len(self.registry.refresh_from_scan(scanned))
        if self.cloud_client.is_enabled:
            updates += len(self.registry.refresh_from_cloud(self.cloud_client.get_devices()))
        if updates:
            self.registry.save()
        return {"updated": updates, "scanned": len(scanned)}

    def discover_with_wizard(
        self,
        *,
        retries: int | None = 5,
        forcescan: bool = True,
        skip_poll: bool = False,
        credentials_path: str | Path | None = None,
        device_output_path: str | Path | None = None,
        snapshot_output_path: str | Path | None = None,
        raw_output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Run TinyTuya wizard discovery and import the results into the registry."""
        cloud_config = self.cloud_client.config
        if cloud_config is None:
            raise RuntimeError("Cloud credentials are required to run TinyTuya wizard discovery")
        if cloud_config.api_device_id.strip().lower() == "scan":
            sample_device = self.registry.all_devices()[0]
            cloud_config = CloudConfig(
                api_key=cloud_config.api_key,
                api_secret=cloud_config.api_secret,
                api_region=cloud_config.api_region,
                api_device_id=sample_device.device_id,
            )

        wizard_devices = self.local_client.run_wizard(
            cloud_config,
            credentials_file=config_store.get_cloud_path(credentials_path),
            device_file=config_store.get_wizard_devices_path(device_output_path),
            snapshot_file=config_store.get_wizard_snapshot_path(snapshot_output_path),
            raw_file=config_store.get_wizard_raw_path(raw_output_path),
            retries=retries,
            forcescan=forcescan,
            skip_poll=skip_poll,
        )
        merged = self.registry.merge_tinytuya_devices(wizard_devices)
        self.registry.save()
        return {
            "wizard_devices": len(wizard_devices),
            "imported": len(merged),
            "device_output_path": str(config_store.get_wizard_devices_path(device_output_path)),
            "snapshot_output_path": str(config_store.get_wizard_snapshot_path(snapshot_output_path)),
            "raw_output_path": str(config_store.get_wizard_raw_path(raw_output_path)),
        }

    def diagnose(self, target: str = "all", *, timeout: float = 1.5) -> dict[str, Any]:
        """Collect local, cloud, and connectivity diagnostics for one or more devices."""
        devices = self.registry.resolve(target)
        network_info = self.local_client.get_local_network_info()
        local_ip = network_info.get("local_ip")

        scanned_devices = self.local_client.scan_devices()
        scanned_by_id = {item.get("device_id"): item for item in scanned_devices if item.get("device_id")}

        cloud_visible = []
        cloud_by_id: dict[str, dict[str, Any]] = {}
        if self.cloud_client.is_enabled:
            cloud_visible = self.cloud_client.get_devices()
            cloud_by_id = {str(item.get("id")): item for item in cloud_visible if item.get("id")}

        device_reports = []
        for device in devices:
            probe = self.local_client.probe_address(device.ip_address, timeout=timeout)
            scanned = scanned_by_id.get(device.device_id)
            cloud = cloud_by_id.get(device.device_id)
            device_reports.append(
                {
                    "slug": device.slug,
                    "name": device.name,
                    "device_id": device.device_id,
                    "configured_ip": device.ip_address,
                    "same_24_prefix_as_laptop": self._same_24_prefix(local_ip, device.ip_address),
                    "tcp_probe": probe,
                    "found_by_local_scan": scanned is not None,
                    "local_scan_ip": scanned.get("ip_address") if scanned else None,
                    "found_in_cloud": cloud is not None,
                    "cloud_name": cloud.get("name") if cloud else None,
                }
            )

        return {
            "local_network": network_info,
            "local_scan": {
                "count": len(scanned_devices),
                "matching_targets": sum(1 for device in devices if device.device_id in scanned_by_id),
            },
            "cloud": {
                "enabled": self.cloud_client.is_enabled,
                "count": len(cloud_visible),
                "matching_targets": sum(1 for device in devices if device.device_id in cloud_by_id),
            },
            "devices": device_reports,
            "likely_causes": self._diagnose_likely_causes(
                network_info=network_info,
                scanned_devices=scanned_devices,
                cloud_visible=cloud_visible,
                device_reports=device_reports,
            ),
        }

    def _refresh_device(self, device_id: str) -> None:
        """Refresh a single device from local scan and optional cloud metadata."""
        scanned = [item for item in self.local_client.scan_devices() if item.get("device_id") == device_id]
        updated = self.registry.refresh_from_scan(scanned)
        if not updated and self.cloud_client.is_enabled:
            cloud_devices = [item for item in self.cloud_client.get_devices() if str(item.get("id")) == device_id]
            updated = self.registry.refresh_from_cloud(cloud_devices)
        if updated:
            self.registry.save()

    def _run_with_fallback(
        self,
        device: DeviceConfig,
        operation: DeviceOperation,
    ) -> CommandResult:
        """Run a local command and retry once after metadata refresh if needed."""
        controller = TuyaBulbController(device, client=self.local_client)
        response = operation(controller)
        if is_success_response(response):
            return CommandResult(target=device.slug, success=True, response=response, transport="local")

        if is_connectivity_error(response):
            self._refresh_device(device.device_id)
            refreshed_device = self.registry.get(device.device_id)
            retry_response = operation(TuyaBulbController(refreshed_device, client=self.local_client))
            return CommandResult(
                target=device.slug,
                success=is_success_response(retry_response),
                response=retry_response,
                transport="local-refreshed",
            )

        return CommandResult(target=device.slug, success=False, response=response, transport="local")

    def _for_target(self, target: str, operation: DeviceOperation) -> list[CommandResult]:
        """Run an operation for each resolved target device."""
        return [self._run_with_fallback(device, operation) for device in self.registry.resolve(target)]

    def status(self, target: str = "all") -> list[CommandResult]:
        """Fetch device status for one or more targets."""
        return self._for_target(target, lambda bulb: bulb.get_status())

    def turn_on(self, target: str) -> list[CommandResult]:
        """Power on one or more targets."""
        return self._for_target(target, lambda bulb: bulb.turn_on())

    def turn_off(self, target: str) -> list[CommandResult]:
        """Power off one or more targets."""
        return self._for_target(target, lambda bulb: bulb.turn_off())

    def set_brightness(self, target: str, brightness: int) -> list[CommandResult]:
        """Set brightness for one or more targets."""
        return self._for_target(target, lambda bulb: bulb.set_brightness(brightness))

    def set_white(
        self,
        target: str,
        brightness: int | None = None,
        colourtemp: int | None = None,
    ) -> list[CommandResult]:
        """Set white mode on one or more targets."""
        return self._for_target(target, lambda bulb: bulb.set_white(brightness=brightness, colourtemp=colourtemp))

    def set_colour(self, target: str, hue: int, saturation: int, value: int) -> list[CommandResult]:
        """Set colour on one or more targets."""
        return self._for_target(target, lambda bulb: bulb.set_colour_hsv(hue, saturation, value))

    def set_mode(self, target: str, mode: str) -> list[CommandResult]:
        """Set mode on one or more targets."""
        return self._for_target(target, lambda bulb: bulb.set_mode(mode))

    def set_raw_dps(self, target: str, dps: int, value: Any) -> list[CommandResult]:
        """Send a raw DPS value to one or more targets."""
        return self._for_target(target, lambda bulb: bulb.set_raw_dps(dps, value))

    def apply_scene(self, scene_name: str) -> list[CommandResult]:
        """Apply a configured scene across its defined targets."""
        results: list[CommandResult] = []
        scene = self.scenes.get(scene_name)
        for action in scene.actions:
            if action.power is not None:
                results.extend(self.turn_on(action.target) if action.power else self.turn_off(action.target))
            if action.mode is not None:
                results.extend(self.set_mode(action.target, action.mode))
            if action.hsv is not None:
                hue, saturation, value = action.hsv
                results.extend(self.set_colour(action.target, hue, saturation, value))
                continue
            if action.mode == "white" or action.colourtemp is not None:
                results.extend(
                    self.set_white(
                        action.target,
                        brightness=action.brightness,
                        colourtemp=action.colourtemp,
                    )
                )
                continue
            if action.brightness is not None:
                results.extend(self.set_brightness(action.target, action.brightness))
        return results
