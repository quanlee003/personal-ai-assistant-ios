"""Start an existing trusted WDA setup. Does not mount, sign, install or pair."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
from urllib.request import urlopen

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.installation_proxy import InstallationProxyService
from pymobiledevice3.usbmux import list_devices


async def identify():
    devices = [d for d in await list_devices() if d.connection_type == 'USB']
    if len(devices) != 1:
        raise RuntimeError('Connect exactly one USB iPhone')
    device = devices[0]
    async with await create_using_usbmux(serial=device.serial, autopair=False) as client:
        if not client.paired or int(client.product_version.split('.')[0]) < 18:
            raise RuntimeError('Requires existing pairing and iOS 18+')
        async with InstallationProxyService(client) as service:
            apps = await service.browse(attributes=['CFBundleIdentifier'])
        candidates = [a['CFBundleIdentifier'] for a in apps
                      if a.get('CFBundleIdentifier', '').startswith('com.facebook.WebDriverAgentRunner.xctrunner')]
        if len(candidates) != 1:
            raise RuntimeError('Expected exactly one installed WDA runner')
    return device.serial, candidates[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=['tunnel', 'wda'])
    args = parser.parse_args()
    udid, bundle = asyncio.run(asyncio.wait_for(identify(), 20))
    root = Path(__file__).resolve().parents[1] / 'artifacts/direct-setup'
    env = os.environ.copy()
    env['GO_IOS_AGENT_PORT'] = '28100'
    if args.component == 'tunnel':
        try:
            with urlopen('http://127.0.0.1:28100/tunnels', timeout=2) as response:
                json.load(response)
        except OSError:
            pass
        else:
            raise RuntimeError('Tunnel registry already running; do not start another')
        command = ['tunnel', 'start', '--userspace', '--tunnel-info-host=127.0.0.1', '--tunnel-info-port=28100']
    else:
        with urlopen('http://127.0.0.1:28100/tunnels', timeout=5) as response:
            tunnels = [t for t in json.load(response) if t.get('udid') == udid and t.get('userspaceTun')]
        if len(tunnels) != 1:
            raise RuntimeError('Expected matching userspace tunnel')
        t = tunnels[0]
        command = ['runwda', '--bundleid=' + bundle, '--testrunnerbundleid=' + bundle,
                   '--xctestconfig=WebDriverAgentRunner.xctest', '--address=' + t['address'],
                   '--rsd-port=' + str(t['rsdPort']), '--userspace-port=' + str(t['userspaceTunPort'])]
    pid_file = root / (args.component + '.pid')
    # Reject a live previous process; never kill an unknown or reused PID.
    if pid_file.exists():
        import psutil
        try:
            process = psutil.Process(int(pid_file.read_text()))
            if Path(process.exe()).resolve() == (root / 'ios.exe').resolve():
                raise RuntimeError('Recorded ios process still running; inspect before restarting')
        except psutil.NoSuchProcess:
            pass
    with (root / (args.component + '-restart.stdout.log')).open('ab') as out, (root / (args.component + '-restart.stderr.log')).open('ab') as err:
        process = subprocess.Popen([str(root / 'ios.exe'), *command, '--udid=' + udid],
                                   env=env, stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
    pid_file.write_text(str(process.pid))
    print('Started process', process.pid, '; verify readiness separately. No UI action sent.')


if __name__ == '__main__':
    main()
