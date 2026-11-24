"""Resolve installed app names locally and verify launches by foreground bundle ID."""
import hashlib
import time

from .commands import normalize
from .control import RunCanceled, check_stop
from .direct import ActionResult

# Public system apps; installation inventory also contains internal services.
SYSTEM_APPS = {
    'com.apple.mobilesafari': ('Safari',),
    'com.apple.mobiletimer': ('Đồng hồ', 'Clock'),
    'com.apple.calculator': ('Máy tính', 'Calculator'),
    'com.apple.mobilenotes': ('Ghi chú', 'Notes'),
    'com.apple.mobilecal': ('Lịch', 'Calendar'),
    'com.apple.Maps': ('Bản đồ', 'Maps'),
    'com.apple.camera': ('Camera', 'Máy ảnh'),
    'com.apple.mobileslideshow': ('Ảnh', 'Photos'),
    'com.apple.MobileSMS': ('Tin nhắn', 'Messages'),
    'com.apple.mobilephone': ('Điện thoại', 'Phone'),
    'com.apple.mobilemail': ('Mail',),
    'com.apple.reminders': ('Lời nhắc', 'Reminders'),
    'com.apple.weather': ('Thời tiết', 'Weather'),
    'com.apple.AppStore': ('App Store',),
    'com.apple.Health': ('Sức khỏe', 'Health'),
    'com.apple.DocumentsApp': ('Tệp', 'Files'),
}


def resolve_app(name, apps):
    query = normalize(name)
    candidates = {}
    for app in apps:
        bundle = app['bundle_id']
        if 'webdriveragent' in bundle.casefold():
            continue
        if app['type'] != 'User' and bundle not in SYSTEM_APPS:
            continue
        names = {normalize(app['name']), *(normalize(a) for a in SYSTEM_APPS.get(bundle, ()))}
        if query in names:
            candidates[bundle] = app
    if len(candidates) == 1:
        return next(iter(candidates.values()))
    if candidates:
        return ActionResult('needs_clarification', 'Có nhiều app cùng tên. Chưa mở app nào; cần phân biệt ứng dụng trước.')
    return ActionResult('target_not_found', f'Chưa tìm thấy app “{name}” có tên phù hợp trong danh sách hỗ trợ trên máy. Hãy xem tên trong Ứng dụng & thiết lập.')


def launch_app(name, *, stop_event=None, on_event=None, dry_run=False, catalog=None, backend_factory=None):
    # Lazy imports avoid the CLI/catalog module cycle.
    from .device_catalog import DeviceCatalog, MESSAGES
    from .wda import WDABackend
    attempted = acknowledged = False
    target_id = observed_id = None
    try:
        check_stop(stop_event)
        if on_event:
            on_event('understanding', 'Đang đối chiếu tên app với iPhone kết nối')
        data = (catalog or DeviceCatalog()).refresh(stop_event, force=True)
        if data.get('status') != 'scanned':
            return ActionResult('error', MESSAGES.get(data.get('status'), 'Chưa quét được app trên máy.'), error_code='app_inventory_unavailable')
        target = resolve_app(name, data['apps'])
        if isinstance(target, ActionResult):
            return target
        target_id = target['bundle_id']
        if on_event:
            on_event('catalog', data)
        if dry_run:
            return ActionResult('dry_run', f"Dự kiến mở {target['name']}; chưa thao tác iPhone.")
        check_stop(stop_event)
        backend = (backend_factory or WDABackend)()
        backend.stop_event = stop_event
        key = hashlib.sha256(backend.tunnel.get('udid', '').encode()).hexdigest()[:24]
        if key != data['device_key']:
            return ActionResult('error', 'Kết nối điều khiển không khớp iPhone vừa quét. Chưa mở app.', error_code='device_mismatch')
        if not backend.ready():
            return ActionResult('error', 'iPhone chưa sẵn sàng để mở app.', error_code='wda_not_ready')
        check_stop(stop_event)
        if on_event:
            on_event('executing', f"Đang mở {target['name']}")
        attempted = True
        backend.open_app(target['bundle_id'])
        acknowledged = True
        if on_event:
            on_event('verifying', 'Đang kiểm tra app ở phía trước')
        # Only observation is polled; launch is never replayed.
        for _ in range(4):
            check_stop(stop_event)
            observed_id = backend.active_bundle()
            if observed_id == target_id:
                return ActionResult('verified_match', f"Đã mở {target['name']}; xác nhận đúng app đang ở phía trước.",
                                    True, True, steps_attempted=1, steps_acknowledged=1,
                                    target_bundle_id=target_id, observed_bundle_id=observed_id,
                                    verification_method='foreground_bundle')
            if stop_event is not None:
                stop_event.wait(.4)
            else:
                time.sleep(.4)
        return ActionResult('verification_uncertain', 'Đã gửi lệnh nhưng chưa thấy đúng app ở phía trước. Không tự mở lại.',
                            True, True, steps_attempted=1, steps_acknowledged=1, error_code='foreground_unconfirmed',
                            target_bundle_id=target_id, observed_bundle_id=observed_id, verification_method='foreground_bundle')
    except (Exception, KeyboardInterrupt) as exc:
        return ActionResult('verification_uncertain' if attempted else 'canceled' if isinstance(exc, (RunCanceled, KeyboardInterrupt)) else 'error',
                            'Đã dừng; chưa xác nhận mở app thành công. Không tự thử lại.',
                            attempted, acknowledged, steps_attempted=int(attempted), steps_acknowledged=int(acknowledged),
                            error_code=getattr(exc, 'code', type(exc).__name__), target_bundle_id=target_id,
                            observed_bundle_id=observed_id, verification_method='foreground_bundle' if attempted else None)
