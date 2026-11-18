"""Bounded direct execution. No TTS imports or automatic fallback."""
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Literal, Protocol
from uuid import uuid4

from .commands import Command, normalize

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

    def to_dict(self):
        return asdict(self)


class DirectBackend(Protocol):
    def ready(self) -> bool: ...
    def screenshot(self, path: Path) -> str: ...
    def open_settings(self) -> None: ...


def validate_command(command: Command | None) -> ActionResult | None:
    if command is None:
        return ActionResult('needs_clarification', 'Chưa có một mục tiêu rõ ràng.')
    if command.action == 'stop':
        return ActionResult('canceled', 'Đã hủy.')
    if command.action != 'open_app':
        return ActionResult('needs_clarification', 'Direct hiện chỉ hỗ trợ mở Cài đặt, không đổi tùy chọn.')
    if set(command.arguments) != {'app_name'} or normalize(command.arguments['app_name']) not in {'cai dat', 'settings'}:
        return ActionResult('target_not_found', 'Ứng dụng chưa thuộc phạm vi direct đã kiểm chứng: chỉ Cài đặt.')
    return None


def execute(command: Command | None, backend: DirectBackend, output_dir: Path, *,
            confirmed: bool = False, dry_run: bool = True,
            verify: Callable[[Path], tuple[str, str]] | None = None) -> ActionResult:
    """Each call is fresh, takes at most one action and never retries a request."""
    invalid = validate_command(command)
    if invalid:
        return invalid
    if dry_run:
        return ActionResult('dry_run', 'Dự kiến mở Cài đặt qua WDA; chưa thực thi.')
    if not confirmed:
        return ActionResult('canceled', 'Chưa được xác nhận, không thực thi.')
    before = after = None
    attempted = acknowledged = False
    try:
        if not backend.ready():
            return ActionResult('error', 'WDA chưa sẵn sàng; không dùng TTS thay thế.')
        folder = Path(output_dir) / ('direct-' + uuid4().hex[:8])
        folder.mkdir(parents=True)
        before = folder / 'before.png'
        backend.screenshot(before)
        attempted = True
        backend.open_settings()
        acknowledged = True
        after = folder / 'after.png'
        backend.screenshot(after)
        if verify is None:
            return ActionResult('action_sent', 'WDA đã trả lời; ảnh sau thao tác chưa được đánh giá.',
                                True, True, str(before), str(after))
        decision, message = verify(after)
        status = {'found': 'verified_match', 'not_found': 'verified_mismatch',
                  'clarify': 'verification_uncertain'}.get(decision, 'verification_uncertain')
        return ActionResult(status, message, True, True, str(before), str(after))
    except (Exception, KeyboardInterrupt) as exc:
        return ActionResult(
            'verification_uncertain' if attempted else ('canceled' if isinstance(exc, KeyboardInterrupt) else 'error'),
            f'{type(exc).__name__}: đã dừng; không tự gửi lại hoặc chuyển sang TTS.',
            attempted, acknowledged,
            str(before) if before and before.exists() else None,
            str(after) if after and after.exists() else None,
        )
