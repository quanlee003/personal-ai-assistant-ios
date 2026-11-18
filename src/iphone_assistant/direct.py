"""Bounded direct execution. No TTS imports or automatic fallback."""
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Literal, Protocol
from uuid import uuid4

from .commands import Command, normalize, parse_command
from .control import RunCanceled, check_stop

BATTERY_TARGET = 'settings.battery'


def is_battery(command: Command | None) -> bool:
    return command is not None and command.action == 'select_target' and command.arguments == {'target': BATTERY_TARGET}


def parse_direct_command(request: str) -> Command:
    if normalize(request) in {'mo pin', 'mo muc pin', 'mo phan pin', 'mo pin trong cai dat',
                               'mo muc pin trong cai dat', 'mo phan pin trong cai dat'}:
        return Command('select_target', {'target': BATTERY_TARGET})
    return parse_command(request)


def action_description(command: Command | None) -> str:
    return 'mở phần Pin trong Cài đặt' if is_battery(command) else 'mở Cài đặt'


def expected_screen(command: Command | None) -> str:
    return ('Trang Pin bên trong ứng dụng Cài đặt đang mở; chỉ có hàng Pin trên trang chính chưa đủ.'
            if is_battery(command) else 'Ứng dụng Cài đặt đang mở ở foreground.')

Status = Literal['canceled', 'needs_clarification', 'target_not_found', 'action_sent',
                 'verified_match', 'verified_mismatch', 'verification_uncertain', 'error', 'dry_run']


@dataclass(frozen=True)
class ActionResult:
    status: Status
    message: str
    action_attempted: bool = False
    action_acknowledged: bool = False
    before_image: str | None = None
    after_image: str | None = None
    steps_attempted: int = 0
    steps_acknowledged: int = 0
    error_code: str | None = None

    def to_dict(self):
        return asdict(self)


class DirectBackend(Protocol):
    def ready(self) -> bool: ...
    def screenshot(self, path: Path) -> None: ...
    def open_settings(self) -> None: ...
    def battery_page_visible(self) -> bool: ...
    def find_battery(self) -> str | None: ...
    def click_battery(self, element_id: str) -> None: ...


def validate_command(command: Command | None) -> ActionResult | None:
    if command is None:
        return ActionResult('needs_clarification', 'Chưa có một mục tiêu rõ ràng.')
    if command.action == 'stop':
        return ActionResult('canceled', 'Đã hủy.')
    if is_battery(command):
        return None
    if command.action != 'open_app':
        return ActionResult('needs_clarification', 'Direct chỉ mở Cài đặt hoặc trang Pin, không đổi tùy chọn.')
    if set(command.arguments) != {'app_name'} or normalize(command.arguments['app_name']) not in {'cai dat', 'settings'}:
        return ActionResult('target_not_found', 'Ứng dụng chưa thuộc phạm vi direct đã kiểm chứng: chỉ Cài đặt.')
    return None


def execute(command: Command | None, backend: DirectBackend, output_dir: Path, *,
            confirmed: bool = False, dry_run: bool = True,
            verify: Callable[[Path], tuple[str, str]] | None = None,
            stop_event=None, on_event=None) -> ActionResult:
    """Fresh bounded workflow: Settings launch, optionally one Battery click; no retries."""
    invalid = validate_command(command)
    if invalid:
        return invalid
    if dry_run:
        return ActionResult('dry_run', f'Dự kiến {action_description(command)} qua WDA; chưa thực thi.')
    if not confirmed:
        return ActionResult('canceled', 'Chưa được xác nhận, không thực thi.')
    before = after = None
    attempted = acknowledged = False
    steps_attempted = steps_acknowledged = 0
    try:
        check_stop(stop_event)
        if not backend.ready():
            return ActionResult('error', 'WDA chưa sẵn sàng; không dùng TTS thay thế.')
        folder = Path(output_dir) / ('direct-' + uuid4().hex[:8])
        folder.mkdir(parents=True)
        before = folder / 'before.png'
        check_stop(stop_event)
        if on_event:
            on_event('observing', 'Đang chụp màn hình trước thao tác')
        backend.screenshot(before)
        check_stop(stop_event)
        if on_event:
            on_event('executing', action_description(command))
        attempted = True
        steps_attempted = 1
        backend.open_settings()
        acknowledged = True
        steps_acknowledged = 1
        check_stop(stop_event)
        if is_battery(command) and not backend.battery_page_visible():
            target = backend.find_battery()
            if target is None:
                after = folder / 'after.png'
                backend.screenshot(after)
                return ActionResult('target_not_found', 'Đã mở Cài đặt nhưng không thấy đúng một mục Pin hợp lệ; không chạm.',
                                    True, True, str(before), str(after), 1, 1, 'battery_target_missing')
            backend.screenshot(folder / 'before-click.png')
            check_stop(stop_event)
            steps_attempted = 2
            backend.click_battery(target)
            steps_acknowledged = 2
        after = folder / 'after.png'
        check_stop(stop_event)
        backend.screenshot(after)
        if is_battery(command) and not backend.battery_page_visible():
            return ActionResult('verification_uncertain', 'Chưa xác nhận được tiêu đề trang Pin; dừng, không chạm lại.',
                                attempted, acknowledged, str(before), str(after), steps_attempted, steps_acknowledged,
                                'battery_page_unconfirmed')
        if verify is None:
            return ActionResult('action_sent', 'WDA đã trả lời; ảnh sau thao tác chưa được đánh giá.',
                                True, True, str(before), str(after), steps_attempted, steps_acknowledged)
        decision, message = verify(after)
        status = {'found': 'verified_match', 'not_found': 'verified_mismatch',
                  'clarify': 'verification_uncertain'}.get(decision, 'verification_uncertain')
        return ActionResult(status, message, True, True, str(before), str(after), steps_attempted, steps_acknowledged)
    except (Exception, KeyboardInterrupt) as exc:
        return ActionResult(
            'verification_uncertain' if attempted else ('canceled' if isinstance(exc, (KeyboardInterrupt, RunCanceled)) else 'error'),
            f'{type(exc).__name__}: đã dừng; không tự gửi lại hoặc chuyển sang TTS.',
            attempted, acknowledged,
            str(before) if before and before.exists() else None,
            str(after) if after and after.exists() else None,
            steps_attempted, steps_acknowledged,
            getattr(exc, 'code', type(exc).__name__),
        )
