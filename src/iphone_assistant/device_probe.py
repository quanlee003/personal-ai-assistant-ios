"""Internal device worker, launched by the desktop in its device Python runtime."""
import asyncio
import hashlib
import json
import sys


async def inspect_device(include_apps=False):
    from pymobiledevice3.usbmux import list_devices
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    devices = [d for d in await list_devices() if d.connection_type == 'USB']
    if len(devices) != 1:
        return {'status': 'disconnected' if not devices else 'multiple_devices'}
    device = devices[0]
    key = hashlib.sha256(device.serial.encode()).hexdigest()[:24]
    if not include_apps:
        return {'status': 'connected', 'device_key': key}
    async with await create_using_usbmux(serial=device.serial, autopair=False) as client:
        if not client.paired:
            return {'status': 'trust_required', 'device_key': key}
        async with InstallationProxyService(client) as service:
            rows = await service.browse(options={'ApplicationType': 'Any'}, attributes=[
                'CFBundleIdentifier', 'CFBundleDisplayName', 'CFBundleName', 'ApplicationType'])
        apps = {a['CFBundleIdentifier']: {
            'bundle_id': a['CFBundleIdentifier'],
            'name': a.get('CFBundleDisplayName') or a.get('CFBundleName') or a['CFBundleIdentifier'],
            'type': a.get('ApplicationType', 'Unknown'),
        } for a in rows if a.get('CFBundleIdentifier')}
        return {'status': 'scanned', 'device_key': key, 'ios': client.product_version,
                'apps': sorted(apps.values(), key=lambda a: a['name'].casefold())}


if __name__ == '__main__':
    try:
        result = asyncio.run(asyncio.wait_for(inspect_device('--apps' in sys.argv), 30))
    except Exception as exc:
        name = type(exc).__name__
        result = {'status': 'trust_required' if 'Pair' in name or 'Password' in name else 'device_error'}
    print(json.dumps(result, ensure_ascii=True))
