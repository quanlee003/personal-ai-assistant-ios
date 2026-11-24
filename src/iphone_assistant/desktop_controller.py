"""Threaded desktop coordinator. Structured events only; no Tk or stdout parsing."""
from dataclasses import dataclass
from queue import Queue
from threading import Event, Lock, Thread
from types import SimpleNamespace
import os

from .control import RunCanceled, check_stop
from .direct_cli import run_logged_turn
from .wda import WDABackend
from .device_catalog import DeviceCatalog
from .phone_setup import open_screen_time
from .screen_reader import read_screen


@dataclass(frozen=True)
class Readiness:
    phone: bool
    microphone: bool
    services: bool
    phone_message: str
    microphone_message: str
    services_message: str

    @property
    def ready(self):
        return self.phone and self.microphone and self.services


def check_readiness(stop_event=None):
    check_stop(stop_event)
    try:
        import sounddevice as sd
        info = sd.query_devices(None, 'input')
        sd.check_input_settings(channels=1, dtype='int16', samplerate=info['default_samplerate'])
        microphone, mic_message = True, str(info['name'])
    except Exception:
        microphone, mic_message = False, 'Chọn microphone đầu vào trong Windows rồi kiểm tra lại.'
    services = all(os.environ.get(name, '').strip() for name in ('DEEPGRAM_API_KEY', 'AI_GATEWAY_API_KEY'))
    services_message = 'Đã có cấu hình Deepgram và AI Gateway' if services else 'Thiếu key trong .env. Xem hướng dẫn thiết lập.'
    check_stop(stop_event)
    try:
        backend = WDABackend()
        backend.stop_event = stop_event
        phone = backend.ready()
        phone_message = 'iPhone đã kết nối' if phone else 'iPhone chưa sẵn sàng'
    except RunCanceled:
        raise
    except Exception:
        phone, phone_message = False, 'Mở khóa iPhone, cắm USB và kiểm tra WDA theo hướng dẫn.'
    check_stop(stop_event)
    return Readiness(phone, microphone, services, phone_message, mic_message, services_message)


class DesktopController:
    def __init__(self, *, preflight=check_readiness, runner=run_logged_turn, catalog=None):
        self.events = Queue()
        self._preflight = preflight
        self._runner = runner
        self._lock = Lock()
        self._busy = False
        self._stop = Event()
        self._worker = None
        self.catalog = catalog or DeviceCatalog()

    @property
    def busy(self):
        with self._lock:
            return self._busy

    def emit(self, kind, value):
        self.events.put((kind, value))

    def _launch(self, function):
        with self._lock:
            if self._busy:
                return False
            self._busy = True
            self._stop = Event()
        self._worker = Thread(target=self._work, args=(function,), daemon=True)
        self._worker.start()
        return True

    def _work(self, function):
        reason = 'complete'
        try:
            reason = function()
        except RunCanceled:
            reason = 'canceled'
        except BaseException as exc:
            # Includes SystemExit from result persistence. Never start another turn.
            reason = 'error'
            self.emit('error', f'{type(exc).__name__}: phiên đã dừng. Xem kết quả local trước khi chạy lại.')
        finally:
            with self._lock:
                self._busy = False
            self.emit('finished', reason)

    def refresh(self):
        def check():
            self.emit('checking', 'Đang kiểm tra kết nối')
            state = self._preflight(self._stop)
            self.emit('readiness', state)
            self.emit('catalog', self.catalog.refresh(self._stop))
            return 'checked'
        return self._launch(check)

    def scan(self, force=True):
        def work():
            if force:
                self.emit('catalog_scanning', None)
            self.emit('catalog', self.catalog.refresh(self._stop, force=force))
            return 'scanned'
        return self._launch(work)

    def read_screen(self, use_ai=False):
        def work():
            try:
                report = read_screen(use_ai=use_ai, stop_event=self._stop, on_event=self.emit)
            except RunCanceled:
                raise
            except Exception as exc:
                report = {'status': 'unavailable', 'message': f'Không đọc được màn hình ({type(exc).__name__}). Kiểm tra WDA, mở khóa iPhone rồi thử lại. Không thao tác trên máy.'}
            self.emit('screen_report', report)
            return 'screen_read'
        return self._launch(work)

    def open_phone_setup(self):
        def work():
            self.emit('checking', 'Đang mở Thời gian sử dụng trên iPhone')
            try:
                state = self.catalog.refresh(self._stop)
                self.emit('catalog', state)
                message = open_screen_time(self._stop, device_key=state.get('device_key'))
            except RunCanceled:
                raise
            except Exception:
                message = 'Chưa mở được mục này. Trên iPhone vào Cài đặt → Thời gian sử dụng → Hoạt động ứng dụng & web. Không tự thử lại.'
            self.emit('setup_result', message)
            return 'setup'
        return self._launch(work)

    def start(self, max_turns=1):
        if not 1 <= max_turns <= 10:
            raise ValueError('Desktop sessions allow 1–10 turns')

        def session():
            self.emit('checking', 'Đang kiểm tra trước khi bắt đầu')
            state = self._preflight(self._stop)
            self.emit('readiness', state)
            check_stop(self._stop)
            if not state.ready:
                return 'not_ready'
            args = SimpleNamespace(auto=True, listen=True, ai=True, execute=True, verify=True,
                                   voice_threshold=500, silence_seconds=1.2)
            for index in range(max_turns):
                check_stop(self._stop)
                self.emit('turn', (index + 1, max_turns))
                result = self._runner(args, stop_event=self._stop, on_event=self.emit)
                self.emit('result', result)
                if self._stop.is_set() or result.status == 'canceled':
                    return 'canceled'
                if result.status in {'error', 'verification_uncertain', 'verified_mismatch'} or (
                        result.status == 'target_not_found' and result.action_attempted):
                    return 'halted'
            return 'complete'
        return self._launch(session)

    def stop(self):
        with self._lock:
            if not self._busy:
                return
            self._stop.set()
        self.emit('stopping', 'Đã yêu cầu dừng. Lệnh đã gửi vẫn có thể hoàn tất; đang chờ phản hồi.')
