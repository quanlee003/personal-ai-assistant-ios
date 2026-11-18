"""WDA over a loopback go-ios userspace tunnel; no audio or cloud."""
import base64
import http.client
import ipaddress
import json
import socket
import struct
from urllib.request import urlopen
from urllib.parse import quote
import xml.etree.ElementTree as ET
from .control import check_stop


class TargetChangedError(RuntimeError):
    code = 'battery_target_changed'


class WDABackend:
    def __init__(self):
        with urlopen('http://127.0.0.1:28100/tunnels', timeout=5) as response:
            tunnels = json.load(response)
        if len(tunnels) != 1 or not tunnels[0].get('userspaceTun'):
            raise RuntimeError('Expected one userspace tunnel')
        self.tunnel = tunnels[0]

    def request(self, method, path, payload=None):
        check_stop(getattr(self, 'stop_event', None))
        t = self.tunnel
        body = json.dumps(payload).encode() if payload is not None else b''
        # One attempt only, including POST timeout. Never replay an uncertain action.
        with socket.create_connection(('127.0.0.1', t['userspaceTunPort']), timeout=30) as sock:
            sock.sendall(ipaddress.IPv6Address(t['address']).packed + struct.pack('<I', 8100))
            headers = (f'{method} {path} HTTP/1.1\r\nHost: localhost\r\n'
                       f'Content-Type: application/json\r\nContent-Length: {len(body)}\r\n'
                       'Connection: close\r\n\r\n').encode()
            check_stop(getattr(self, 'stop_event', None))
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

    def ready(self):
        return self.request('GET', '/status')['value'].get('ready') is True

    def open_settings(self):
        self.session_id = None
        self._battery_element = None
        result = self.request('POST', '/session', {'capabilities': {'alwaysMatch': {
            'bundleId': 'com.apple.Preferences', 'shouldTerminateApp': False}}})
        self.session_id = result.get('sessionId') or result.get('value', {}).get('sessionId')

    def session_request(self, method, path, payload=None):
        if not self.session_id:
            raise RuntimeError('No fresh WDA session')
        return self.request(method, '/session/' + quote(self.session_id, safe='') + path, payload)

    def settings_foreground(self):
        return self.session_request('GET', '/wda/activeAppInfo')['value'].get('bundleId') == 'com.apple.Preferences'

    def battery_page_visible(self):
        if not self.settings_foreground():
            return False
        root = ET.fromstring(self.session_request('GET', '/source')['value'])
        bars = [e for e in root.iter() if e.tag == 'XCUIElementTypeNavigationBar' and e.get('visible') == 'true']
        return len(bars) == 1 and bars[0].get('name') in {'Pin', 'Battery'}

    def find_battery(self):
        self._battery_element = None
        if not self.settings_foreground():
            return None
        # Identifier observed on device; no text fallback, scrolling or coordinate guess.
        query = "type == 'XCUIElementTypeButton' AND name == 'com.apple.settings.battery' AND visible == 1 AND enabled == 1"
        matches = self.session_request('POST', '/elements', {'using': 'predicate string', 'value': query})['value']
        if len(matches) != 1:
            return None
        self._battery_element = matches[0].get('element-6066-11e4-a52e-4f735466cecf') or matches[0].get('ELEMENT')
        return self._battery_element

    def click_battery(self, element_id):
        if not element_id or element_id != self._battery_element:
            raise TargetChangedError('Target not from this observation')
        self._battery_element = None  # Consume once, including on timeout.
        path = '/element/' + quote(element_id, safe='')
        if not self.settings_foreground():
            raise TargetChangedError('Foreground changed')
        checks = {'/attribute/name': 'com.apple.settings.battery', '/attribute/type': 'XCUIElementTypeButton',
                  '/displayed': True, '/enabled': True}
        for suffix, expected in checks.items():
            if self.session_request('GET', path + suffix)['value'] != expected:
                raise TargetChangedError('Element changed')
        if not self.settings_foreground():
            raise TargetChangedError('Foreground changed')
        self.session_request('POST', path + '/click', {})
