"""Native Windows voice-control window; workers never touch Tk widgets."""
import os
from datetime import datetime
from pathlib import Path
from queue import Empty
import tkinter as tk
from tkinter import ttk

from .desktop_controller import DesktopController
from .direct_cli import PROJECT_ROOT
from .device_catalog import MESSAGES
from .screen_reader import describe_report
from .onboarding import SetupPreferences, setup_step

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
    def __init__(self, root, controller=None, preferences=None):
        self.root = root
        self.controller = controller or DesktopController()
        self.readiness = None
        self.stopping = False
        self.closing = False
        self.last_record = None
        self.catalog_data = None
        self.catalog_window = None
        self.preferences = preferences or SetupPreferences()
        self.setup_notice = ''
        self.forced_personalization = False
        self.root.title('Trợ lý iPhone')
        self.root.geometry('1100x700')
        self.root.minsize(980, 680)
        self.root.configure(bg=BG)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self._style()
        self._build()
        self.root.after(50, self._poll)
        self.root.after(100, self.refresh)
        self.root.after(12000, self._auto_scan)

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
        ttk.Button(header, text='Công cụ', command=self.show_tools).pack(side='right', padx=8)
        ttk.Button(header, text='Cá nhân hóa', command=self.show_personalization).pack(side='right')
        self._label(self.root, 'Nói yêu cầu trên PC. Theo dõi thao tác trên iPhone.', color=MUTED).pack(
            anchor='w', padx=24, pady=(0, 16))

        self.setup_frame = tk.Frame(self.root, bg='white', padx=32, pady=28)
        self.setup_title = self._label(self.setup_frame, 'Đang kiểm tra kết nối', 20, bold=True, wraplength=800)
        self.setup_title.pack(fill='x', pady=(0, 18))
        self.setup_detail = self._label(self.setup_frame, '', 12, MUTED, wraplength=800)
        self.setup_detail.pack(fill='x', pady=(0, 20))
        self.setup_action = ttk.Button(self.setup_frame, text='Kiểm tra lại', style='Primary.TButton', command=self.setup_next)
        self.setup_action.pack(anchor='w', pady=8)
        self.setup_continue = ttk.Button(self.setup_frame, text='Tiếp tục vào trợ lý', command=self.finish_setup)
        self.setup_continue.pack(anchor='w', pady=8)
        self.setup_later = ttk.Button(self.setup_frame, text='Để sau', command=self.finish_setup)
        self.setup_later.pack(anchor='w', pady=8)
        self.setup_stop = ttk.Button(self.setup_frame, text='Dừng', command=self.stop)
        self.setup_feedback = self._label(self.setup_frame, '', 11, MUTED, wraplength=800)
        self.setup_feedback.pack(fill='x', pady=12)
        self.tools_window = tk.Toplevel(self.root)
        self.tools_window.title('Công cụ kiểm thử')
        self.tools_window.geometry('480x760')
        self.tools_window.configure(bg=BG)
        self.tools_window.protocol('WM_DELETE_WINDOW', self.tools_window.withdraw)
        self.tools_window.withdraw()
        body = self.main_body = tk.Frame(self.root, bg=BG)
        body.pack(fill='both', expand=True, padx=24)
        body.columnconfigure(0, weight=0, minsize=0)
        body.columnconfigure(1, weight=1, minsize=290)
        body.columnconfigure(2, weight=1, minsize=290)
        body.rowconfigure(0, weight=1)
        left = tk.Frame(self.tools_window, bg=BG, padx=20, pady=12)
        left.pack(fill='both', expand=True)
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
        ttk.Button(left, text='Ứng dụng & thiết lập', command=self.show_catalog).pack(fill='x', pady=(12, 0))

        self._label(middle, 'Phiên giọng nói', 14, bold=True).pack(anchor='w')
        self.turn = self._label(middle, 'Chưa bắt đầu', 10, MUTED)
        self.turn.pack(anchor='w', pady=(6, 12))
        self.phase = self._label(middle, 'Đang chuẩn bị', 18, bold=True, wraplength=280)
        self.phase.pack(anchor='w', fill='x')
        self.message = self._label(middle, 'Đang kiểm tra kết nối…', 11, MUTED, wraplength=280)
        self.message.pack(anchor='w', fill='x', pady=(8, 12))
        self._label(left, 'Số lượt trong phiên', 10).pack(anchor='w')
        self.turn_count = ttk.Combobox(left, values=('1', '2', '5', '10'), state='readonly', width=6)
        self.turn_count.set('1')
        self.turn_count.pack(anchor='w', pady=(6, 12))
        self.start_button = ttk.Button(middle, text='Bắt đầu nói', style='Primary.TButton', command=self.start)
        self.start_button.pack(fill='x')
        self.stop_button = ttk.Button(middle, text='Dừng', command=self.stop)
        self.stop_button.pack(fill='x', pady=(8, 12))
        self._label(middle, 'Thử nói', 10, MUTED).pack(anchor='w', pady=(4, 6))
        self._label(middle, '“Mở Zalo” · “Mở Safari”\n“Mở phần Pin trong Cài đặt”', 11,
                    wraplength=280).pack(anchor='w')
        self._label(middle, 'Không cần xác nhận từng lượt.',
                    10, MUTED, wraplength=280).pack(anchor='w', pady=(10, 0))

        self._label(right, 'Kết quả gần nhất', 14, bold=True).pack(anchor='w')
        self.read_button = ttk.Button(left, text='Đọc màn hình', command=self.read_screen)
        self.read_button.pack(fill='x', pady=(12, 4))
        self.screen_ai = tk.BooleanVar(value=False)
        self.screen_ai_check = tk.Checkbutton(left, text='Gửi ảnh tới AI Gateway để mô tả',
                                             variable=self.screen_ai, bg='white', fg=INK,
                                             font=('Segoe UI', 9), wraplength=240, anchor='w', justify='left')
        self.screen_ai_check.pack(anchor='w')
        self.result_title = self._label(right, 'Chưa có yêu cầu', 12, MUTED, True, wraplength=280)
        self.result_title.pack(fill='x', pady=(12, 12))
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
        self.record_button = ttk.Button(left, text='Mở kết quả local', command=self.open_result)
        self.record_button.pack(fill='x', pady=(16, 0))
        self.record_button.state(['disabled'])
        self._label(self.root,
                    'Chỉ thu âm khi bạn bấm Bắt đầu. Audio gửi Deepgram; câu và ảnh màn hình gửi AI Gateway.',
                    10, MUTED, wraplength=900).pack(side='bottom', before=body, anchor='w', padx=24, pady=(12, 12))
        for frame in (middle, right):
            frame.bind('<Configure>', lambda e, f=frame: self._wrap(f))
        self._controls(True)

    def show_tools(self):
        self.tools_window.deiconify()
        self.tools_window.lift()

    def show_personalization(self):
        self.forced_personalization = True
        self.setup_notice = ''
        self._render_setup()

    def _render_setup(self):
        step = setup_step(self.readiness, self.catalog_data, self.preferences.dismissed)
        if step == 'ready' and self.forced_personalization:
            step = 'personalization'
        self.current_setup_step = step
        if step == 'ready':
            self.setup_frame.pack_forget()
            self.main_body.pack(fill='both', expand=True, padx=24)
            return
        self.main_body.pack_forget()
        self.setup_frame.pack(fill='both', expand=True, padx=24, pady=(0, 16))
        title, detail, action = {
            'checking': ('Đang kiểm tra kết nối', 'Kết nối iPhone bằng USB và giữ máy mở khóa. Trợ lý sẽ kiểm tra các điều kiện để bắt đầu.', 'Kiểm tra lại'),
            'connection': ('Kết nối iPhone', MESSAGES.get((self.catalog_data or {}).get('status'), 'Chưa đọc được iPhone. Kết nối USB, mở khóa và chọn Tin cậy khi iOS hỏi.'), 'Kiểm tra lại'),
            'phone': ('Chuẩn bị điều khiển iPhone', 'Đã đọc được thiết bị nhưng kết nối điều khiển chưa sẵn sàng. Giữ iPhone mở khóa và khởi chạy WDA.\n\nNếu chưa thiết lập: trên iPhone vào Cài đặt → Quyền riêng tư & Bảo mật → Chế độ nhà phát triển. Làm theo yêu cầu trên iPhone và hướng dẫn thiết lập.\n\nChưa thể tự mở trang khi WDA chưa hoạt động. App chưa xác định riêng trạng thái từng quyền.', 'Xem hướng dẫn thiết lập'),
            'microphone': ('Chuẩn bị microphone', 'Chọn microphone đầu vào trên Windows và cho phép ứng dụng desktop dùng microphone. App sẽ kiểm tra lại tự động; bước này chưa thu âm.', 'Mở cài đặt microphone'),
            'services': ('Kết nối dịch vụ AI', 'Chưa có đủ cấu hình dịch vụ nhận giọng nói và AI. Làm theo phần cấu hình trong hướng dẫn; app sẽ kiểm tra lại tự động. Việc có cấu hình chưa xác nhận key hợp lệ.', 'Mở hướng dẫn cấu hình'),
            'personalization': ('Giúp AI hiểu thói quen của bạn', 'Khuyên dùng · Không bắt buộc\n\nBật Thời gian sử dụng để chuẩn bị dữ liệu về những ứng dụng bạn thường dùng. Khi tính năng đọc báo cáo được triển khai và bạn cho phép, thông tin này sẽ giúp AI đề xuất hỗ trợ phù hợp và ưu tiên học app của bạn.\n\nBản hiện tại chỉ mở trang thiết lập, chưa đọc báo cáo hay nhận biết thói quen. Bật trên iPhone không đồng nghĩa cho trợ lý thu thập hoặc chia sẻ dữ liệu.', 'Mở Thời gian sử dụng'),
        }[step]
        self.setup_title.configure(text=title)
        self.setup_detail.configure(text=detail)
        self.setup_action.configure(text=action)
        self.setup_feedback.configure(text=self.setup_notice)
        self.setup_continue.pack_forget()
        self.setup_later.pack_forget()
        if step == 'personalization':
            if self.setup_notice:
                self.setup_continue.pack(anchor='w', pady=8, before=self.setup_feedback)
            self.setup_later.pack(anchor='w', pady=8, before=self.setup_feedback)

    def setup_next(self):
        step = self.current_setup_step
        if step == 'personalization':
            self.setup_notice = 'Đang mở trang trên iPhone. Bạn tự quyết định bật; chưa có dữ liệu báo cáo nào được thu thập.'
            self.open_phone_setup()
        elif step == 'microphone':
            self._open('ms-settings:privacy-microphone')
        elif step in {'phone', 'services'}:
            self.open_guide()
        else:
            self.refresh()

    def finish_setup(self):
        key = (self.catalog_data or {}).get('device_key')
        if not key or not (self.readiness and self.readiness.ready):
            return
        try:
            self.preferences.finish(key)
        except OSError:
            self.setup_notice = 'Chưa lưu được lựa chọn trên PC. Kiểm tra quyền ghi thư mục runtime rồi thử lại.'
        else:
            self.forced_personalization = False
            self.setup_notice = ''
        self._render_setup()

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
        self._render_setup()
        for button in (self.setup_action, self.setup_continue, self.setup_later):
            button.state(['disabled'] if busy else ['!disabled'])
        if busy:
            self.setup_stop.pack(anchor='w', pady=8)
        else:
            self.setup_stop.pack_forget()
        self.setup_stop.state(['disabled'] if self.stopping else ['!disabled'])
        self.read_button.state(['disabled'] if busy or not (self.readiness and self.readiness.phone) else ['!disabled'])
        self.screen_ai_check.configure(state='disabled' if busy else 'normal')
        if self.catalog_window and self.catalog_window.winfo_exists():
            self.scan_button.state(['disabled'] if busy else ['!disabled'])
            self.setup_button.state(['disabled'] if busy or not (self.readiness and self.readiness.phone
                                   and self.catalog_data and self.catalog_data.get('status') == 'scanned') else ['!disabled'])
        self.start_button.state(['disabled'] if busy or not (self.readiness and self.readiness.ready) else ['!disabled'])
        self.refresh_button.state(['disabled'] if busy else ['!disabled'])
        self.stop_button.state(['!disabled'] if busy and not self.stopping else ['disabled'])
        if busy:
            self.stop_button.pack(fill='x', pady=(8, 12), after=self.start_button)
        else:
            self.stop_button.pack_forget()
        self.turn_count.configure(state='disabled' if busy else 'readonly')

    def refresh(self):
        if self.controller.refresh():
            self.stopping = False
            self._controls(True)

    def read_screen(self):
        if self.controller.read_screen(use_ai=self.screen_ai.get()):
            self.stopping = False
            self.last_record = None
            self.record_button.state(['disabled'])
            self.result_title.configure(text='Đang đọc màn hình…', fg=INK)
            self._set_result('Đang lấy trạng thái hiện tại. Không tự bấm hoặc nhập nội dung. Kết quả lưu local.')
            self._controls(True)

    def _auto_scan(self):
        if not self.closing and not self.controller.busy:
            if (self.controller.refresh() if self.current_setup_step != 'ready' and self.current_setup_step != 'personalization'
                    else self.controller.scan(force=False)):
                self._controls(True)
        if not self.closing:
            self.root.after(12000, self._auto_scan)

    def scan(self):
        if self.controller.scan():
            self._controls(True)

    def open_phone_setup(self):
        if self.controller.open_phone_setup():
            self._controls(True)

    def show_catalog(self):
        if self.catalog_window and self.catalog_window.winfo_exists():
            self.catalog_window.lift()
            return
        window = self.catalog_window = tk.Toplevel(self.root)
        window.title('Ứng dụng & thiết lập iPhone')
        window.geometry('900x620')
        window.minsize(760, 540)
        window.configure(bg=BG)
        toolbar = tk.Frame(window, bg=BG)
        toolbar.pack(fill='x', padx=20, pady=16)
        self._label(toolbar, 'Ứng dụng & thiết lập', 18, bold=True).pack(side='left')
        self.scan_button = ttk.Button(toolbar, text='Quét lại', command=self.scan)
        self.scan_button.pack(side='right')
        self.catalog_status = self._label(window, 'Đang chờ quét thiết bị…', 10, MUTED, wraplength=830)
        self.catalog_status.pack(fill='x', padx=20, pady=(0, 12))
        tabs = ttk.Notebook(window)
        tabs.pack(fill='both', expand=True, padx=20, pady=(0, 16))
        apps = ttk.Frame(tabs, padding=12)
        settings = ttk.Frame(tabs, padding=12)
        tabs.add(apps, text='Ứng dụng trên máy')
        tabs.add(settings, text='Điều kiện & quyền')
        self.app_filter = tk.StringVar(value='')
        ttk.Label(apps, text='Tìm tên app hoặc bundle ID (bao gồm thành phần hệ thống)').pack(anchor='w')
        search = ttk.Entry(apps, textvariable=self.app_filter)
        search.pack(fill='x', pady=(6, 10))
        self.app_filter.trace_add('write', lambda *_: self._render_catalog())
        table_frame = ttk.Frame(apps)
        table_frame.pack(fill='both', expand=True)
        self.apps_table = ttk.Treeview(table_frame, columns=('name', 'type', 'bundle'), show='headings')
        for key, title, width in [('name', 'Tên ứng dụng', 230), ('type', 'Loại', 90), ('bundle', 'Bundle ID', 380)]:
            self.apps_table.heading(key, text=title)
            self.apps_table.column(key, width=width, minwidth=70)
        scrollbar = ttk.Scrollbar(table_frame, command=self.apps_table.yview)
        self.apps_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.apps_table.pack(fill='both', expand=True)
        requirement_frame = ttk.Frame(settings)
        requirement_frame.pack(fill='both', expand=True)
        self.requirements = tk.Text(requirement_frame, wrap='word', font=('Segoe UI', 11), bg='white', fg=INK,
                                    relief='flat', padx=12, pady=12, height=12)
        requirement_scroll = ttk.Scrollbar(requirement_frame, command=self.requirements.yview)
        self.requirements.configure(yscrollcommand=requirement_scroll.set)
        requirement_scroll.pack(side='right', fill='y')
        self.requirements.pack(fill='both', expand=True)
        self.setup_button = ttk.Button(settings, text='Mở Thời gian sử dụng trên iPhone', command=self.open_phone_setup)
        self.setup_button.pack(anchor='w', pady=(12, 0))
        self.setup_message = ttk.Label(settings, text='Chỉ mở trang thiết lập. Bạn tự bật hoặc cấp quyền trên iPhone.', wraplength=790)
        self.setup_message.pack(anchor='w', pady=(8, 0))
        self._render_catalog()
        self._controls(self.controller.busy)

    def _render_catalog(self):
        if not self.catalog_window or not self.catalog_window.winfo_exists():
            return
        data = self.catalog_data or {'status': 'unknown'}
        self.apps_table.delete(*self.apps_table.get_children())
        query = self.app_filter.get().casefold()
        rows = data.get('apps', [])
        for row in rows:
            if query in (row['name'] + ' ' + row['bundle_id']).casefold():
                self.apps_table.insert('', 'end', values=(row['name'], row['type'], row['bundle_id']))
        count = sum(row['type'] == 'User' for row in rows)
        scanned = data.get('status') == 'scanned'
        captured = datetime.fromisoformat(data['captured_at']).astimezone().strftime('%d/%m/%Y %H:%M') if scanned else ''
        status = (f"{count} app người dùng · {len(rows)-count} mục khác/hệ thống · Cập nhật: {captured}"
                  if scanned else MESSAGES.get(data.get('status'), 'Chưa quét thiết bị. Bấm Quét lại.'))
        self.catalog_status.configure(text=status)
        wda_ready = self.readiness and self.readiness.phone
        lines = [
            'QUÉT DANH SÁCH APP — BẮT BUỘC',
            'USB & Tin cậy máy tính: ' + ('đã kiểm chứng qua lần đọc app thành công.' if scanned else 'chưa kiểm chứng. Mở khóa iPhone, kết nối USB và chấp nhận Tin cậy nếu iOS hỏi.'),
            '', 'ĐIỀU KHIỂN MÀN HÌNH — BẮT BUỘC KHI THAO TÁC',
            'WDA: ' + ('đang phản hồi.' if wda_ready else 'chưa sẵn sàng. Xem Hướng dẫn ở cửa sổ chính.'),
            'Developer Mode, runner đã ký và kết nối kiểm thử: cần cho WDA; không đọc riêng được trạng thái từng mục từ lần quét app.',
            '', 'THỜI GIAN SỬ DỤNG — TÙY CHỌN',
            'Chưa kiểm tra. Không cần bật để quét app. Bấm nút bên dưới để mở trang trên iPhone; nếu chưa bật Hoạt động ứng dụng & web, bạn tự bật khi muốn thu thập báo cáo.',
            'Bản này chưa đọc báo cáo sử dụng hoặc cấp quyền Screen Time API cho app.',
            '', 'HEALTHKIT / SỨC KHỎE — KHÔNG CẦN CHO TÍNH NĂNG NÀY',
            'Xin quyền Sức khỏe hay Family Controls cần app iOS riêng và capability tương ứng. App Windows hiện tại không thể hiện hộp thoại cấp các quyền này.',
            '', 'Không có một công tắc “full access”. Danh sách lưu local theo thiết bị, không gửi AI/cloud. System có cả thành phần nội bộ, không phải tất cả đều có icon.',
        ]
        self.requirements.configure(state='normal')
        self.requirements.delete('1.0', 'end')
        self.requirements.insert('1.0', '\n'.join(lines))
        self.requirements.configure(state='disabled')

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
        if kind == 'screen_report':
            self.result_title.configure(text='Màn hình vừa đọc' if value.get('status') == 'read' else 'Chưa đọc được màn hình', fg=INK)
            self._set_result(describe_report(value))
            self.last_record = Path(value['record']) if value.get('record') else None
            self.record_button.state(['!disabled'] if self.last_record else ['disabled'])
            return
        if kind == 'finished' and value == 'screen_read':
            self.stopping = False
            self.phase.configure(text='Đã kết thúc đọc', fg=INK)
            self.message.configure(text='Kết quả bên phải là trạng thái tại thời điểm đọc. Chưa thao tác iPhone.')
            self._controls(False)
            return
        if kind == 'catalog':
            unchanged = self.catalog_data == value
            self.catalog_data = value
            if not unchanged:
                self._render_catalog()
            return
        if kind == 'catalog_scanning':
            if self.catalog_window and self.catalog_window.winfo_exists():
                self.catalog_status.configure(text='Đang kiểm tra và quét thiết bị…')
            return
        if kind == 'setup_result':
            self.setup_notice = value
            self._render_setup()
            if self.catalog_window and self.catalog_window.winfo_exists():
                self.setup_message.configure(text=value)
            return
        if kind == 'finished' and value in {'scanned', 'setup'}:
            self.stopping = False
            self._controls(False)
            if value == 'setup':
                self.phase.configure(text='Đã kết thúc kiểm tra')
                self.message.configure(text='Trang thiết lập đã được kiểm tra. Chưa đọc báo cáo sử dụng.')
            return
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
            self._render_catalog()
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
                            'iPhone đã kết nối. Bấm Bắt đầu nói để gửi yêu cầu.' if ready else 'Làm theo bước thiết lập đang hiển thị.'),
                'not_ready': ('Chưa sẵn sàng', 'Làm theo bước thiết lập đang hiển thị rồi thử lại.'),
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
