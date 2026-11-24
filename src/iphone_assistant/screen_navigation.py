"""Observed native tab/back navigation with one click and no retries."""
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


def target_names(target):
    return TABS.get(target, (target,))


def xpath_literal(value):
    if '"' not in value:
        return '"' + value + '"'
    if "'" not in value:
        return "'" + value + "'"
    return 'concat(' + ',\'"\','.join('"' + part + '"' for part in value.split('"')) + ')'


def tab_nodes(xml, target, back=False):
    names = {normalize(name) for name in target_names(target)}
    return [node for bar in ET.fromstring(xml).iter('XCUIElementTypeNavigationBar' if back else 'XCUIElementTypeTabBar')
            for node in bar.iter('XCUIElementTypeButton')
            if node.get('visible') == 'true' and node.get('enabled') == 'true'
            and normalize(node.get('label') or node.get('name') or '') in names]


def selected(node):
    return node.get('selected') == 'true' or node.get('value') == '1'


def navigation_titles(xml):
    return tuple((node.get('name') or node.get('label') or '').strip()
                 for node in ET.fromstring(xml).iter('XCUIElementTypeNavigationBar')
                 if node.get('visible') == 'true')


BACK = ('Back', 'Quay lại', 'Trở lại')


def navigate_back(**kwargs):
    return navigate_tab('Back', _back=True, **kwargs)


def navigate_tab(target, *, dry_run=False, stop_event=None, on_event=None, backend_factory=WDABackend, _back=False):
    if not isinstance(target, str) or not target.strip() or len(target) > 120:
        return ActionResult('target_not_found', 'Tên tab trống hoặc quá dài.')
    names = BACK if _back else target_names(target)
    title = 'Quay lại' if _back else names[0]
    def candidates(xml):
        if not _back:
            return tab_nodes(xml, target)
        return [node for name in BACK for node in tab_nodes(xml, name, back=True)]
    if dry_run:
        return ActionResult('dry_run', f'Dự kiến {title} trên giao diện hiện tại; chưa thao tác.')
    attempted = acknowledged = False
    observed = None
    bundle = None
    def result(status, message, code=None):
        return ActionResult(status, message, attempted, acknowledged,
                            steps_attempted=int(attempted), steps_acknowledged=int(acknowledged),
                            error_code=code, target_bundle_id=bundle, observed_bundle_id=observed,
                            verification_method='navigation_title_changed' if _back else 'selected_tab')
    try:
        check_stop(stop_event)
        backend = backend_factory()
        backend.stop_event = stop_event
        if backend.request('GET', '/wda/locked')['value']:
            return result('target_not_found', 'Hãy mở khóa iPhone trước.')
        backend.observe_current_app()
        observed = backend.active_bundle()
        bundle = observed
        if not bundle or bundle == 'com.apple.springboard' or (target in TABS and bundle != CLOCK):
            return result('target_not_found', 'Chưa ở ứng dụng phù hợp; chưa bấm gì.')
        if on_event:
            on_event('observing', 'Đang tìm nút điều hướng trên màn hình hiện tại')
        source = backend.session_request('GET', '/source')['value']
        titles = navigation_titles(source)
        nodes = candidates(source)
        observed = backend.active_bundle()
        if observed != bundle:
            return result('target_not_found', 'Ứng dụng đã thay đổi; chưa bấm.')
        if len(nodes) != 1:
            return result('target_not_found', 'Không thấy đúng một nút điều hướng phù hợp; chưa bấm.')
        if _back and (len(titles) != 1 or not titles[0]):
            return result('target_not_found', 'Chưa xác định trang để kiểm tra thao tác quay lại.')
        if not _back and selected(nodes[0]):
            return result('verified_match', f'Đang ở tab {title}; không cần bấm lại.')
        label = nodes[0].get('label') or nodes[0].get('name')
        name_query = f'@label={xpath_literal(label)} or @name={xpath_literal(label)}'
        container = 'XCUIElementTypeNavigationBar' if _back else 'XCUIElementTypeTabBar'
        query = f'//{container}//XCUIElementTypeButton[({name_query}) and @visible="true" and @enabled="true"]'
        matches = backend.session_request('POST', '/elements', {'using': 'xpath', 'value': query})['value']
        if len(matches) != 1:
            return result('target_not_found', 'Nút điều hướng không còn duy nhất; chưa bấm.')
        element = matches[0].get('element-6066-11e4-a52e-4f735466cecf') or matches[0].get('ELEMENT')
        if not element:
            return result('target_not_found', 'Không có định danh nút; chưa bấm.')
        path = '/element/' + quote(element, safe='')
        # Re-check the actual element and foreground immediately before the click.
        for attribute, allowed in [('visible', {'true', '1'}), ('enabled', {'true', '1'}),
                                   ('label', {label})]:
            value = backend.session_request('GET', path + '/attribute/' + attribute)['value']
            if str(value).lower() not in {str(v).lower() for v in allowed}:
                return result('target_not_found', 'Nút điều hướng đã thay đổi; chưa bấm.')
        fresh = backend.session_request('GET', '/source')['value']
        fresh_nodes = candidates(fresh)
        if len(fresh_nodes) != 1 or ET.tostring(fresh_nodes[0]) != ET.tostring(nodes[0]) or navigation_titles(fresh) != titles:
            return result('target_not_found', 'Giao diện đã thay đổi; chưa bấm.')
        observed = backend.active_bundle()
        if observed != bundle or backend.request('GET', '/wda/locked')['value']:
            return result('target_not_found', 'Màn hình đã thay đổi; chưa bấm.')
        check_stop(stop_event)
        if on_event:
            on_event('executing', f'Đang thực hiện: {title}')
        attempted = True
        backend.session_request('POST', path + '/click', {})
        acknowledged = True
        if on_event:
            on_event('verifying', 'Đang kiểm tra giao diện sau điều hướng')
        for _ in range(4):
            check_stop(stop_event)
            observed = backend.active_bundle()
            if observed != bundle:
                break
            source = backend.session_request('GET', '/source')['value']
            nodes = candidates(source)
            new_titles = navigation_titles(source)
            verified = (len(new_titles) == 1 and bool(new_titles[0]) and new_titles != titles) if _back else (len(nodes) == 1 and selected(nodes[0]))
            if verified and backend.active_bundle() == bundle:
                return result('verified_match', 'Đã quay lại; tiêu đề trang điều hướng đã đổi.' if _back else f'Đã chuyển sang {title}; xác nhận tab đang được chọn.')
            if stop_event is None:
                time.sleep(.25)
            else:
                stop_event.wait(.25)
        return result('verification_uncertain', 'Đã gửi một lần bấm nhưng chưa xác nhận được điều hướng; không tự bấm lại.')
    except (Exception, KeyboardInterrupt) as exc:
        return result('verification_uncertain' if attempted else 'canceled' if isinstance(exc, (RunCanceled, KeyboardInterrupt)) else 'error',
                      'Đã dừng; không tự gửi lại thao tác.', type(exc).__name__)
