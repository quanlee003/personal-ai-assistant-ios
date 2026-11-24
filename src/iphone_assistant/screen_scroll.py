"""Single vertical scroll, verified by movement of observed UI elements."""
import time
import xml.etree.ElementTree as ET

from .control import RunCanceled, check_stop
from .direct import ActionResult
from .screen_navigation import navigation_titles
from .wda import WDABackend

CONTAINERS = {'XCUIElementTypeScrollView', 'XCUIElementTypeTable', 'XCUIElementTypeCollectionView'}


def scroll_snapshot(xml):
    root = ET.fromstring(xml)
    regions = [node for node in root.iter() if node.tag in CONTAINERS and node.get('visible') == 'true']
    if len(regions) != 1:
        return None
    region = regions[0]
    items = {}
    duplicates = set()
    for node in region.iter():
        name = node.get('label') or node.get('name')
        if node.get('visible') != 'true' or not name or node.tag in CONTAINERS:
            continue
        key = (node.tag, name)
        if key in items:
            duplicates.add(key)
        try:
            items[key] = float(node.attrib['y'])
        except (KeyError, ValueError):
            continue
    for key in duplicates:
        items.pop(key, None)
    return (region.tag, region.get('name'), navigation_titles(xml)), items


def moved(before, after, direction):
    if after is None or before[0] != after[0]:
        return False
    deltas = [after[1][key] - y for key, y in before[1].items() if key in after[1]]
    expected = [delta for delta in deltas if (delta <= -20 if direction == 'down' else delta >= 20)]
    opposite = [delta for delta in deltas if (delta >= 20 if direction == 'down' else delta <= -20)]
    return len(expected) >= 2 and not opposite


def scroll_screen(direction, *, dry_run=False, stop_event=None, on_event=None, backend_factory=WDABackend):
    if direction not in {'up', 'down'}:
        return ActionResult('needs_clarification', 'Chỉ hỗ trợ cuộn lên hoặc xuống một lần.')
    label = 'xuống' if direction == 'down' else 'lên'
    if dry_run:
        return ActionResult('dry_run', f'Dự kiến cuộn {label} một lần; chưa thao tác.')
    attempted = acknowledged = False
    bundle = observed = None
    def result(status, message, code=None):
        return ActionResult(status, message, attempted, acknowledged,
                            steps_attempted=int(attempted), steps_acknowledged=int(acknowledged),
                            target_bundle_id=bundle, observed_bundle_id=observed,
                            verification_method='visible_element_movement', error_code=code)
    try:
        check_stop(stop_event)
        backend = backend_factory()
        backend.stop_event = stop_event
        if backend.request('GET', '/wda/locked')['value']:
            return result('target_not_found', 'Hãy mở khóa iPhone trước.')
        backend.observe_current_app()
        bundle = observed = backend.active_bundle()
        if not bundle or bundle == 'com.apple.springboard':
            return result('target_not_found', 'Hãy mở một trang có nội dung cuộn trước.')
        if on_event:
            on_event('observing', 'Đang kiểm tra vùng cuộn trên màn hình')
        before = scroll_snapshot(backend.session_request('GET', '/source')['value'])
        if before is None or len(before[1]) < 2:
            return result('target_not_found', 'Chưa thấy đúng một vùng cuộn có đủ thành phần để kiểm tra; chưa cuộn.')
        fresh = scroll_snapshot(backend.session_request('GET', '/source')['value'])
        observed = backend.active_bundle()
        if fresh != before or observed != bundle or backend.request('GET', '/wda/locked')['value']:
            return result('target_not_found', 'Giao diện vừa thay đổi; chưa cuộn.')
        check_stop(stop_event)
        if on_event:
            on_event('executing', f'Đang cuộn {label} một lần')
        attempted = True
        backend.session_request('POST', '/wda/scroll', {'direction': direction, 'distance': .4})
        acknowledged = True
        if on_event:
            on_event('verifying', 'Đang kiểm tra vị trí nội dung sau cuộn')
        for _ in range(4):
            check_stop(stop_event)
            observed = backend.active_bundle()
            if observed != bundle:
                break
            after = scroll_snapshot(backend.session_request('GET', '/source')['value'])
            if moved(before, after, direction) and backend.active_bundle() == bundle:
                return result('verified_match', f'Đã cuộn {label}; nhận thấy nội dung dịch chuyển đúng chiều.')
            if stop_event is None:
                time.sleep(.25)
            else:
                stop_event.wait(.25)
        return result('verification_uncertain', 'Đã gửi một lần cuộn nhưng chưa thấy đủ chuyển động để xác minh. Có thể ở đầu/cuối trang; không tự cuộn lại.')
    except (Exception, KeyboardInterrupt) as exc:
        return result('verification_uncertain' if attempted else 'canceled' if isinstance(exc, (RunCanceled, KeyboardInterrupt)) else 'error',
                      'Đã dừng; không tự gửi lại lần cuộn.', type(exc).__name__)
