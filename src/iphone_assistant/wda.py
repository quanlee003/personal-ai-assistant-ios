"""WDA over a loopback go-ios userspace tunnel; no audio or cloud."""
import base64
import hashlib
import http.client
import ipaddress
import json
from pathlib import Path
import socket
import struct
from urllib.request import urlopen


class WDABackend:
    def __init__(self):
        with urlopen('http://127.0.0.1:28100/tunnels', timeout=5) as response:
            tunnels = json.load(response)
        if len(tunnels) != 1 or not tunnels[0].get('userspaceTun'):
            raise RuntimeError('Expected one userspace tunnel')
        self.tunnel = tunnels[0]

    def request(self, method, path, payload=None):
        t = self.tunnel
        body = json.dumps(payload).encode() if payload is not None else b''
        # One attempt only, including POST timeout. Never replay an uncertain action.
        with socket.create_connection(('127.0.0.1', t['userspaceTunPort']), timeout=30) as sock:
            sock.sendall(ipaddress.IPv6Address(t['address']).packed + struct.pack('<I', 8100))
            headers = (f'{method} {path} HTTP/1.1\r\nHost: localhost\r\n'
                       f'Content-Type: application/json\r\nContent-Length: {len(body)}\r\n'
                       'Connection: close\r\n\r\n').encode()
            sock.sendall(headers + body)
            response = http.client.HTTPResponse(sock)
            response.begin()
            data = json.loads(response.read())
            value = data.get('value')
            if response.status >= 400 or (isinstance(value, dict) and value.get('error')):
                raise RuntimeError(f'WDA HTTP {response.status}: ' + str(value.get('error') if isinstance(value, dict) else 'error'))
            return data

    def screenshot(self, path):
        raw = base64.b64decode(self.request('GET', '/screenshot')['value'], validate=True)
        if raw[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Screenshot is not PNG')
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def ready(self):
        return self.request('GET', '/status')['value'].get('ready') is True

    def open_settings(self):
        self.request('POST', '/session', {'capabilities': {'alwaysMatch': {
            'bundleId': 'com.apple.Preferences', 'shouldTerminateApp': False}}})
