"""Inspect or explicitly mount DDI over the existing loopback go-ios tunnel."""
import argparse
import asyncio
import ipaddress
import json
import struct
from urllib.request import urlopen

from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.services.cryptexd import CryptexdService
from pymobiledevice3.services.mobile_image_mounter import LATEST_DDI_BUILD_ID


async def run(mount=False):
    with urlopen('http://127.0.0.1:28100/tunnels', timeout=5) as response:
        tunnels = json.load(response)
    if len(tunnels) != 1 or not tunnels[0].get('userspaceTun'):
        raise RuntimeError('Expected exactly one userspace tunnel')
    tunnel = tunnels[0]

    async def dial(host, port, **kwargs):
        if host != tunnel['address']:
            raise ValueError('Unexpected device endpoint')
        reader, writer = await asyncio.open_connection('127.0.0.1', tunnel['userspaceTunPort'])
        writer.write(ipaddress.IPv6Address(host).packed + struct.pack('<I', port))
        await writer.drain()
        return reader, writer

    async with RemoteServiceDiscoveryService(
        (tunnel['address'], tunnel['rsdPort']), open_connection=dial
    ) as rsd:
        print('RSD connected; iOS:', rsd.product_version, flush=True)
        print('Expected DDI build:', LATEST_DDI_BUILD_ID, flush=True)
        names = rsd.peer_info.get('Services', {})
        print('XCTest services:', [n for n in names if 'testmanagerd' in n], flush=True)
        service = CryptexdService(rsd)
        if mount:
            installed = await service.auto_install_ddi()
            print('DDI installed:', installed.identifier, installed.version, flush=True)
        else:
            installed = await service.copy_installed()
            print('Installed cryptex identifiers:', [x.identifier for x in installed], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mount', action='store_true', help='Sends personalization data to Apple and installs DDI')
    args = parser.parse_args()
    try:
        asyncio.run(asyncio.wait_for(run(args.mount), timeout=120))
    except Exception as exc:
        print('Failed:', type(exc).__name__, str(exc)[:600])
        raise SystemExit(1)
