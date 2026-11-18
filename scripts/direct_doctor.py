"""Read-only USB/WDA preflight. No pairing, install, launch, TTS or cloud calls."""
import argparse
import asyncio
import json


def wda_candidates(apps):
    """Heuristic only: custom bundle names may not contain these markers."""
    return [a.get("CFBundleIdentifier", "") for a in apps if any(
        marker in (str(a.get("CFBundleIdentifier", "")) + " "
                   + str(a.get("CFBundleName", ""))).lower()
        for marker in ("webdriver", "xctrunner", "appium")
    )]


async def inspect_device(devices, create_client, service_type):
    devices = [d for d in devices if d.connection_type == "USB"]
    result = {"status": "blocked", "usb_devices": len(devices),
              "direct_action_verified": False}
    if len(devices) != 1:
        result["reason"] = "Connect exactly one USB device; no automatic selection."
        return result
    device = devices[0]
    client = await create_client(serial=device.serial, autopair=False)
    async with client:
        result["device"] = {k: await client.get_value(key=k) for k in (
            "ProductType", "ProductVersion", "BuildVersion")}
        result["paired"] = client.paired
        if not client.paired:
            result["reason"] = "Existing pairing unavailable; Trust requires user approval."
            return result
        result["developer_mode"] = await client.get_value(
            domain="com.apple.security.mac.amfi", key="DeveloperModeStatus")
        async with service_type(client) as service:
            apps = await service.browse(attributes=["CFBundleIdentifier", "CFBundleName"])
            result["wda_candidates"] = wda_candidates(apps)
    # Merely test the conventional device port through USB; never send an action.
    try:
        connection = await asyncio.wait_for(device.connect(8100), 5)
        connection.close()
        result["device_port_8100"] = "open_unverified_service"
    except Exception as exc:
        result["device_port_8100"] = type(exc).__name__
    result["reason"] = (
        "This USB-only preflight does not test actions or the userspace tunnel. "
        "A closed USB port does not mean tunnel WDA is unavailable. "
        "Use scripts/wda_smoke.py without --execute-settings for current WDA readiness; "
        "this report does not supersede previously reviewed action evidence."
    )
    return result


async def probe():
    from pymobiledevice3.usbmux import list_devices
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    return await inspect_device(await list_devices(), create_using_usbmux,
                                InstallationProxyService)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=25)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        parser.error("timeout must be between 1 and 120 seconds")
    try:
        result = asyncio.run(asyncio.wait_for(probe(), args.timeout))
    except Exception as exc:
        # Exception messages may include identifiers or pairing details.
        result = {"status": "error", "error_type": type(exc).__name__,
                  "direct_action_verified": False}
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 1  # Preflight never certifies the physical milestone.


if __name__ == "__main__":
    raise SystemExit(main())
