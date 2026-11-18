"""Native Windows voice-control window; workers never touch Tk widgets."""
import os
from pathlib import Path
from queue import Empty
import tkinter as tk
from tkinter import ttk

from .desktop_controller import DesktopController
from .direct_cli import PROJECT_ROOT

BG = '#F3F5F6'
INK = '#192D38'
MUTED = '#536570'
ACCENT = '#086A63'
WARNING = '#945218'
ERROR = '#A52B32'
RESULT_TITLES = {
    'verified_match': 'Đã kiểm tra thành công',
    'verified_mismatch': 'Màn hình chưa đúng yêu cầu',
    'verification_uncertain': 'Chưa xác định được kết quả',
    'action_sent': 'Đã gửi lệnh, chưa xác minh',
    'canceled': 'Đã dừng', 'error': 'Không thể hoàn tất',
    'needs_clarification': 'Cần nói rõ yêu cầu',
    'target_not_found': 'Chưa tìm thấy mục cần mở', 'dry_run': 'Chỉ xem trước',
}


class DesktopApp:
    def __init__(self, root, controller=None):
        self.root = root
        self.controller = controller or DesktopController()
        self.readiness = None
        self.stopping = False
        self.closing = False
        self.last_record = None
        self.root.title('Trợ lý iPhone')
        self.root.geometry('1100x700')
        self.root.minsize(980, 680)
        self.root.configure(bg=BG)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self._style()
        self._build()
        self.root.after(50, self._poll)
        self.root.after(100, self.refresh)

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background=BG, foreground=INK)
        style.configure('TButton', padding=(12, 9), borderwidth=1)
        style.map('TButton', background=[('active', '#E3E9EC')],
                  foreground=[('disabled', '#697780')])
        style.configure('Primary.TButton', background=ACCENT, foreground='white',
                        font=('Segoe UI', 11, 'bold'))
        style.map('Primary.TButton', background=[('disabled', '#DCE3E5'), ('active', '#07574F')],
                  foreground=[('disabled', '#56646D'), ('!disabled', 'white')])
        style.configure('TCombobox', padding=6)

    def _label(self, parent, text='', size=11, color=INK, bold=False, **kw):
        return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color,
                        font=('Segoe UI', size, 'bold' if bold else 'normal'),
                        anchor='w', justify='left', **kw)

    def _build(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill='x', padx=24, pady=(16, 10))
        self._label(header, 'Trợ lý iPhone', 20, bold=True).pack(side='left')
        ttk.Button(header, text='Hướng dẫn', command=self.open_guide).pack(side='right')
        self._label(self.root, 'Nói yêu cầu trên PC. Theo dõi thao tác trên iPhone.', color=MUTED).pack(
            anchor='w', padx=24, pady=(0, 16))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill='both', expand=True, padx=24)
        body.columnconfigure(0, weight=0, minsize=220)
        body.columnconfigure(1, weight=1, minsize=290)
        body.columnconfigure(2, weight=1, minsize=290)
        body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=BG, padx=0)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 20))
        middle = tk.Frame(body, bg='white', padx=16, pady=16)
        middle.grid(row=0, column=1, sticky='nsew', padx=(0, 16))
        right = tk.Frame(body, bg='white', padx=16, pady=16)
        right.grid(row=0, column=2, sticky='nsew')

        self._label(left, 'Kết nối', 14, bold=True).pack(anchor='w', pady=(0, 24))
        self.check_labels = {}
        for key, title in [('phone', 'iPhone'), ('microphone', 'Microphone'), ('services', 'Dịch vụ AI')]:
            self._label(left, title, bold=True).pack(anchor='w')
            label = self._label(left, 'Chưa kiểm tra', 10, MUTED, wraplength=195)
            label.pack(anchor='w', fill='x', pady=(5, 24))
            self.check_labels[key] = label
        self.refresh_button = ttk.Button(left, text='Kiểm tra lại', command=self.refresh)
        self.refresh_button.pack(fill='x', pady=(0, 16))
        self._label(left, 'Giữ iPhone mở khóa và kết nối USB. WDA cần được khởi chạy trước.',
                    10, MUTED, wraplength=195).pack(anchor='w')

        self._label(middle, 'Phiên giọng nói', 14, bold=True).pack(anchor='w')
        self.turn = self._label(middle, 'Chưa bắt đầu', 10, MUTED)
        self.turn.pack(anchor='w', pady=(6, 12))
        self.phase = self._label(middle, 'Đang chuẩn bị', 18, bold=True, wraplength=280)
        self.phase.pack(anchor='w', fill='x')
        self.message = self._label(middle, 'Đang kiểm tra kết nối…', 11, MUTED, wraplength=280)
        self.message.pack(anchor='w', fill='x', pady=(8, 12))
        self._label(middle, 'Số lượt trong phiên', 10).pack(anchor='w')
        self.turn_count = ttk.Combobox(middle, values=('1', '2', '5', '10'), state='readonly', width=6)
        self.turn_count.set('1')
        self.turn_count.pack(anchor='w', pady=(6, 12))
        self.start_button = ttk.Button(middle, text='Bắt đầu', style='Primary.TButton', command=self.start)
        self.start_button.pack(fill='x')
        self.stop_button = ttk.Button(middle, text='Dừng', command=self.stop)
        self.stop_button.pack(fill='x', pady=(8, 12))
        self._label(middle, 'Thử nói', 10, MUTED).pack(anchor='w', pady=(4, 6))
        self._label(middle, '“Mở Cài đặt”\n“Mở phần Pin trong Cài đặt”', 11,
                    wraplength=280).pack(anchor='w')
        self._label(middle, 'Không cần xác nhận từng lượt.',
                    10, MUTED, wraplength=280).pack(anchor='w', pady=(10, 0))

        self._label(right, 'Kết quả gần nhất', 14, bold=True).pack(anchor='w')
        self.result_title = self._label(right, 'Chưa có yêu cầu', 12, MUTED, True, wraplength=280)
        self.result_title.pack(fill='x', pady=(24, 12))
        text_frame = tk.Frame(right, bg='white')
        text_frame.pack(fill='both', expand=True)
        self.result_text = tk.Text(text_frame, wrap='word', width=26, height=8,
                                   bg='white', fg=INK, font=('Segoe UI', 11), relief='flat',
                                   padx=0, pady=4, cursor='arrow', selectbackground='#CEEAE5')
        scroll = ttk.Scrollbar(text_frame, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.result_text.pack(side='left', fill='both', expand=True)
        self._set_result('Sau khi bạn nói, câu nhận dạng và kết quả kiểm tra sẽ hiện ở đây.')
        self.record_button = ttk.Button(right, text='Mở kết quả local', command=self.open_result)
        self.record_button.pack(fill='x', pady=(16, 0))
        self.record_button.state(['disabled'])
        self._label(self.root,
                    'Chỉ thu âm khi bạn bấm Bắt đầu. Audio gửi Deepgram; câu và ảnh màn hình gửi AI Gateway.',
                    10, MUTED, wraplength=900).pack(side='bottom', before=body, anchor='w', padx=24, pady=(12, 12))
        for frame in (middle, right):
            frame.bind('<Configure>', lambda e, f=frame: self._wrap(f))
        self._controls(True)

    def _wrap(self, frame):
        for child in frame.winfo_children():
            if isinstance(child, tk.Label) and int(child.cget('wraplength')):
                child.configure(wraplength=max(180, frame.winfo_width() - 40))

    def _set_result(self, text):
        self.result_text.configure(state='normal')
        self.result_text.delete('1.0', 'end')
        self.result_text.insert('1.0', text)
        self.result_text.configure(state='disabled')

    def _controls(self, busy):
        self.start_button.state(['disabled'] if busy or not (self.readiness and self.readiness.ready) else ['!disabled'])
        self.refresh_button.state(['disabled'] if busy else ['!disabled'])
        self.stop_button.state(['!disabled'] if busy and not self.stopping else ['disabled'])
        self.turn_count.configure(state='disabled' if busy else 'readonly')

    def refresh(self):
        if self.controller.refresh():
            self.stopping = False
            self._controls(True)

    def start(self):
        if self.controller.start(int(self.turn_count.get())):
            self.stopping = False
            self._controls(True)

    def stop(self):
        self.stopping = True
        self.controller.stop()
        self.phase.configure(text='Đang dừng…')
        self._controls(True)

    def close(self):
        if self.controller.busy:
            self.closing = True
            self.stop()
        else:
            self.root.destroy()

    def _poll(self):
        try:
            while True:
                kind, value = self.controller.events.get_nowait()
                self._event(kind, value)
        except Empty:
            pass
        if self.closing and not self.controller.busy:
            self.root.destroy()
            return
        self.root.after(50, self._poll)

    def _event(self, kind, value):
        phases = {'checking': 'Đang kiểm tra', 'listening': 'Đang nghe',
                  'transcribing': 'Nhận dạng lời nói', 'understanding': 'Đang hiểu yêu cầu',
                  'observing': 'Quan sát iPhone', 'executing': 'Đang thao tác',
                  'verifying': 'Kiểm tra kết quả', 'stopping': 'Đang dừng…'}
        if kind in phases and (not self.stopping or kind == 'stopping'):
            self.phase.configure(text=phases[kind], fg=ACCENT if kind == 'listening' else INK)
            self.message.configure(text=value)
        elif kind == 'readiness':
            self.readiness = value
            for key, label in self.check_labels.items():
                ok = getattr(value, key)
                label.configure(text=('Sẵn sàng' if ok and key != 'services' else 'Đã cấu hình' if ok else 'Cần kiểm tra')
                                + '\n' + getattr(value, key + '_message'), fg=ACCENT if ok else WARNING)
        elif kind == 'turn':
            self.transcript = ''
            self.last_record = None
            self.record_button.state(['disabled'])
            self.turn.configure(text=f'Lượt {value[0]} / {value[1]}')
        elif kind == 'transcript':
            self.transcript = value
            self.result_title.configure(text='Đã nghe yêu cầu', fg=INK)
            self._set_result(value + '\n\nĐang xử lý…')
        elif kind == 'record':
            self.last_record = Path(value)
            self.record_button.state(['!disabled'])
        elif kind == 'result':
            self.result_title.configure(text=RESULT_TITLES.get(value.status, value.status),
                                        fg=ACCENT if value.status == 'verified_match' else WARNING)
            transcript = getattr(self, 'transcript', '')
            self._set_result((f'Bạn nói: {transcript}\n\n' if transcript else '') + value.message +
                             f'\n\nBước đã bắt đầu: {value.steps_attempted}\nBước WDA phản hồi: {value.steps_acknowledged}')
        elif kind == 'error':
            self.result_title.configure(text='Phiên đã dừng do lỗi', fg=ERROR)
            self._set_result(value)
        elif kind == 'finished':
            self.stopping = False
            ready = self.readiness and self.readiness.ready
            title, message = {
                'checked': ('Sẵn sàng' if ready else 'Chưa sẵn sàng',
                            'Bấm Bắt đầu, rồi nói yêu cầu.' if ready else 'Kiểm tra các mục ở bên trái rồi bấm Kiểm tra lại.'),
                'not_ready': ('Chưa sẵn sàng', 'Kiểm tra các mục ở bên trái rồi thử lại.'),
                'complete': ('Đã kết thúc phiên', 'Xem kết quả bên phải. Bấm Bắt đầu để nói yêu cầu mới.'),
                'canceled': ('Đã dừng phiên', 'Microphone đã đóng. Xem kết quả nếu lệnh đã được gửi.'),
                'halted': ('Phiên đã dừng', 'Xem kết quả trước khi bắt đầu lại. Không tự gửi lại lệnh.'),
                'error': ('Phiên đã dừng do lỗi', 'Xem thông tin bên phải và kiểm tra lại kết nối.'),
            }.get(value, ('Đã dừng', ''))
            self.phase.configure(text=title, fg=INK)
            self.message.configure(text=message)
            self._controls(False)

    def _open(self, path):
        try:
            os.startfile(str(path))
        except OSError:
            self.message.configure(text='Không mở được đường dẫn. Xem README trong thư mục dự án.')

    def open_guide(self):
        self._open(PROJECT_ROOT / 'README.md')

    def open_result(self):
        if self.last_record:
            self._open(self.last_record.parent)


def main():
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env', override=False)
    root = tk.Tk()
    DesktopApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
