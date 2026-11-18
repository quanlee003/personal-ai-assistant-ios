"""Bounded navigation to Screen Time; never presses an enable/authorization button."""
import time
import hashlib
import xml.etree.ElementTree as ET

from .control import check_stop
from .wda import WDABackend


def open_screen_time(stop_event=None, backend_factory=WDABackend, device_key=None):
    backend = backend_factory()
    backend.stop_event = stop_event
    check_stop(stop_event)
    if device_key is None or hashlib.sha256(backend.tunnel.get('udid', '').encode()).hexdigest()[:24] != device_key:
        raise RuntimeError('WDA tunnel does not match scanned device')
    backend.open_settings()

    def source():
        check_stop(stop_event)
        if not backend.settings_foreground():
            raise RuntimeError('Settings is not foreground')
        return ET.fromstring(backend.session_request('GET', '/source')['value'])

    def click(name, kind):
        check_stop(stop_event)
        matches = backend.session_request('POST', '/elements', {
            'using': 'predicate string',
            'value': f"type == '{kind}' AND name == '{name}' AND visible == 1 AND enabled == 1",
        })['value']
        if len(matches) != 1:
            raise RuntimeError('Target is not unique')
        key = matches[0].get('element-6066-11e4-a52e-4f735466cecf') or matches[0]['ELEMENT']
        check_stop(stop_event)
        if not backend.settings_foreground():
            raise RuntimeError('Foreground changed')
        backend.session_request('POST', '/element/' + key + '/click', {})

    # Navigate back to the root if Settings was left inside another page.
    for _ in range(5):
        root = source()
        names = {e.get('name') for e in root.iter() if e.get('visible') == 'true'}
        if names & {'Bật Hoạt động ứng dụng & web', 'Turn On App & Website Activity'}:
            return 'iPhone đang hiện yêu cầu bật Hoạt động ứng dụng & web. Chưa có quyền hoặc báo cáo nào được cấp cho app; bạn tự quyết định bật trên iPhone.'
        bars = {e.get('name') for e in root.iter() if e.tag == 'XCUIElementTypeNavigationBar'}
        if bars & {'Thời gian sử dụng', 'Screen Time'}:
            return 'Đã mở Thời gian sử dụng. Chọn Hoạt động ứng dụng & web để xem báo cáo hoặc tự bật nếu muốn.'
        if bars & {'Cài đặt', 'Settings'}:
            break
        if 'BackButton' not in names:
            raise RuntimeError('Cannot return to Settings root')
        click('BackButton', 'XCUIElementTypeButton')
        time.sleep(.3)
    else:
        raise RuntimeError('Navigation limit reached')
    for _ in range(5):
        root = source()
        targets = [e for e in root.iter() if e.get('name') == 'com.apple.settings.screenTime'
                   and e.tag == 'XCUIElementTypeButton' and e.get('visible') == 'true']
        if len(targets) == 1:
            # Avoid a partially visible row behind the bottom bar.
            window = next((e for e in root.iter() if e.tag == 'XCUIElementTypeWindow'), None)
            row = targets[0]
            if window is not None and float(row.get('y', 0)) + float(row.get('height', 0)) < float(window.get('height', 0)) - 60:
                click('com.apple.settings.screenTime', 'XCUIElementTypeButton')
                time.sleep(.5)
                observed = source()
                if any(e.tag == 'XCUIElementTypeNavigationBar' and e.get('name') in
                       {'Thời gian sử dụng', 'Screen Time'} for e in observed.iter()):
                    return 'Đã mở Thời gian sử dụng trên iPhone. Chọn Hoạt động ứng dụng & web; việc bật do bạn quyết định.'
                raise RuntimeError('Destination not verified; no repeated tap')
        backend.session_request('POST', '/wda/scroll', {'direction': 'down', 'distance': .4})
    raise RuntimeError('Screen Time not found within navigation limit')
