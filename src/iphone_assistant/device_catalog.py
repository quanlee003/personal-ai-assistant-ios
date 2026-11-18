"""Local per-device inventory. No cloud calls or UI navigation during scanning."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from .control import check_stop
from .direct_cli import PROJECT_ROOT

MESSAGES = {
    'disconnected': 'Chưa thấy iPhone USB. Kết nối cáp và mở khóa điện thoại.',
    'multiple_devices': 'Có nhiều iPhone. Chỉ kết nối một máy để quét.',
    'trust_required': 'Mở khóa iPhone và chọn Tin cậy máy tính khi iOS hỏi, rồi bấm Quét lại.',
    'runtime_missing': 'Thiếu môi trường thiết bị trên PC. Xem hướng dẫn thiết lập trong README.',
    'device_error': 'Chưa đọc được thiết bị. Kiểm tra cáp, mở khóa iPhone và quyền Tin cậy rồi quét lại.',
    'storage_error': 'Đã đọc thiết bị nhưng không lưu được danh mục trên PC. Kiểm tra quyền ghi thư mục ứng dụng rồi quét lại.',
}


def probe(include_apps=False, stop_event=None):
    runtime = PROJECT_ROOT / 'artifacts/direct-setup/venv-ddi/Scripts/python.exe'
    if not runtime.exists():
        # Also supports an installed desktop environment with the device extra.
        import importlib.util
        if importlib.util.find_spec('pymobiledevice3') is None:
            return {'status': 'runtime_missing'}
        runtime = Path(sys.executable)
    command = [str(runtime), str(Path(__file__).with_name('device_probe.py'))]
    if include_apps:
        command.append('--apps')
    check_stop(stop_event)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + 40
    try:
        while True:
            check_stop(stop_event)
            try:
                output, _ = process.communicate(timeout=.1)
                if process.returncode:
                    return {'status': 'device_error'}
                try:
                    data = json.loads(output)
                except (ValueError, UnicodeError):
                    return {'status': 'device_error'}
                return data if isinstance(data, dict) else {'status': 'device_error'}
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    return {'status': 'device_error'}
    finally:
        if process.poll() is None:
            process.kill()  # This worker only reads the device, never sends UI actions.
        process.communicate()


class DeviceCatalog:
    def __init__(self, reader=probe, folder=None):
        self.reader = reader
        self.folder = folder or PROJECT_ROOT / 'runtime/device-profiles'
        self.current = None

    def refresh(self, stop_event=None, force=False):
        identity = self.reader(False, stop_event)
        if identity.get('status') != 'connected':
            self.current = None
            return identity
        key = identity['device_key']
        if not force and self.current and self.current['device_key'] == key:
            return self.current
        self.current = None
        data = self.reader(True, stop_event)
        check_stop(stop_event)
        if data.get('device_key') != key or data.get('status') != 'scanned':
            self.current = None
            return {'status': data.get('status', 'device_error')} if data.get('status') != 'scanned' else {'status': 'device_error'}
        data['captured_at'] = datetime.now(timezone.utc).isoformat()
        data['screen_time'] = 'unknown'
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            path = self.folder / (key + '.json')
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temporary, path)
        except OSError:
            return {'status': 'storage_error'}
        self.current = data
        return data
