"""One observed Clock tab selection, with no click retries."""
import time
from urllib.parse import quote
import xml.etree.ElementTree as ET

from .commands import normalize
from .control import RunCanceled, check_stop
from .direct import ActionResult
from .wda import WDABackend

CLOCK = 'com.apple.mobiletimer'
TABS = {
    'world_clock': ('Giờ quốc tế', 'World Clock'),
    'alarms': ('Báo thức', 'Alarms', 'Alarm'),
    'stopwatch': ('Bấm giờ', 'Stopwatch'),
    'timers': ('Hẹn giờ', 'Timers', 'Timer'),
}


def tab_nodes(xml, target):
    names = {normalize(name) for name in TABS[target]}
    return [node for bar in ET.fromstring(xml).iter('XCUIElementTypeTabBar')
            for node in bar.iter('XCUIElementTypeButton')
            if node.get('visible') == 'true' and node.get('enabled') == 'true'
            and normalize(node.get('label') or node.get('name') or '') in names]


def selected(node):
    return node.get('selected') == 'true' or node.get('value') == '1'


def navigate_tab(target, *, dry_run=False, stop_event=None, on_event=None, backend_factory=WDABackend):
    if target not in TABS:
        return ActionResult('target_not_found', 'Hiện chỉ hỗ trợ chuyển tab trong Đồng hồ.')
    if dry_run:
        return ActionResult('dry_run', f'Dự kiến chuyển tab {TABS[target][0]} nếu Đồng hồ đang mở.')
    attempted = acknowledged = False
    observed = None
    def result(status, message, code=None):
        return ActionResult(status, message, attempted, acknowledged,
                            steps_attempted=int(attempted), steps_acknowledged=int(acknowledged),
                            error_code=code, target_bundle_id=CLOCK, observed_bundle_id=observed,
                            verification_method='selected_tab')
    try:
        check_stop(stop_event)
        backend = backend_factory()
        backend.stop_event = stop_event
        if backend.request('GET', '/wda/locked')['value']:
            return result('target_not_found', 'Hãy mở khóa iPhone và mở Đồng hồ trước.')
        backend.observe_current_app()
        observed = backend.active_bundle()
        if observed != CLOCK:
            return result('target_not_found', 'Hãy mở Đồng hồ trước; chưa bấm gì trên màn hình hiện tại.')
        if on_event:
            on_event('observing', 'Đang tìm tab trên màn hình Đồng hồ hiện tại')
        nodes = tab_nodes(backend.session_request('GET', '/source')['value'], target)
        observed = backend.active_bundle()
        if observed != CLOCK:
            return result('target_not_found', 'Ứng dụng đã thay đổi; chưa bấm.')
        if len(nodes) != 1:
            return result('target_not_found', 'Không thấy đúng một tab phù hợp; chưa bấm.')
        if selected(nodes[0]):
            return result('verified_match', f'Đang ở tab {TABS[target][0]}; không cần bấm lại.')
        # Fixed names only; never interpolate model output into an XPath.
        names = ' or '.join(f'@label="{name}" or @name="{name}"' for name in TABS[target])
        query = f'//XCUIElementTypeTabBar//XCUIElementTypeButton[({names}) and @visible="true" and @enabled="true"]'
        matches = backend.session_request('POST', '/elements', {'using': 'xpath', 'value': query})['value']
        if len(matches) != 1:
            return result('target_not_found', 'Tab không còn duy nhất; chưa bấm.')
        element = matches[0].get('element-6066-11e4-a52e-4f735466cecf') or matches[0].get('ELEMENT')
        if not element:
            return result('target_not_found', 'Không có định danh tab; chưa bấm.')
        path = '/element/' + quote(element, safe='')
        # Re-check the actual element and foreground immediately before the click.
        for attribute, allowed in [('visible', {'true', '1'}), ('enabled', {'true', '1'}),
                                   ('label', set(TABS[target]))]:
            value = backend.session_request('GET', path + '/attribute/' + attribute)['value']
            if str(value).lower() not in {str(v).lower() for v in allowed}:
                return result('target_not_found', 'Tab đã thay đổi; chưa bấm.')
        observed = backend.active_bundle()
        if observed != CLOCK or backend.request('GET', '/wda/locked')['value']:
            return result('target_not_found', 'Màn hình đã thay đổi; chưa bấm.')
        check_stop(stop_event)
        if on_event:
            on_event('executing', f'Đang chuyển tab {TABS[target][0]}')
        attempted = True
        backend.session_request('POST', path + '/click', {})
        acknowledged = True
        if on_event:
            on_event('verifying', 'Đang kiểm tra tab được chọn')
        for _ in range(4):
            check_stop(stop_event)
            observed = backend.active_bundle()
            if observed != CLOCK:
                break
            nodes = tab_nodes(backend.session_request('GET', '/source')['value'], target)
            if len(nodes) == 1 and selected(nodes[0]) and backend.active_bundle() == CLOCK:
                return result('verified_match', f'Đã chuyển sang {TABS[target][0]}; xác nhận tab đang được chọn.')
            if stop_event is None:
                time.sleep(.25)
            else:
                stop_event.wait(.25)
        return result('verification_uncertain', 'Đã gửi một lần bấm nhưng chưa xác nhận được tab; không tự bấm lại.')
    except (Exception, KeyboardInterrupt) as exc:
        return result('verification_uncertain' if attempted else 'canceled' if isinstance(exc, (RunCanceled, KeyboardInterrupt)) else 'error',
                      'Đã dừng; không tự gửi lại thao tác.', type(exc).__name__)
