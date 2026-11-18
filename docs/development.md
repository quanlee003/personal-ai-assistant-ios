# Phát triển và kiểm tra

## Môi trường ứng dụng

Python 3.11+, chạy từ thư mục repository:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Dependency runtime nằm trong `pyproject.toml`. Không có extra `windows`, `speech`
hay `intent` nữa; các thư viện cần thiết cho workflow direct là dependency chính.
Sau khi thay entry point, chạy lại `pip install -e .` để cập nhật executable.
Môi trường thiết bị/go-ios/DDI tách riêng, xem [setup Windows](direct-windows.md).

## Entry point

Lệnh chính đã kiểm tra trên máy hiện tại:

```powershell
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli "mở Cài đặt"
```

Package cũng đăng ký `iphone-assistant = iphone_assistant.direct_cli:main`.
Launcher `.venv/Scripts/iphone-assistant.exe` mới tạo bị Windows Application
Control chặn trên máy hiện tại; chưa kiểm thử chạy executable này. Dùng lệnh
Python module phía trên, không đổi/tắt chính sách bảo mật hệ thống.

Mặc định preview. `--auto` chủ động bật microphone/cloud/thao tác; không dùng cờ
này trong test hoặc smoke check thông thường. Cách dùng tại [README](../README.md).

## Kiểm tra trước khi commit

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
git diff --check
```

Test suite mock microphone, cloud và backend; không tác động iPhone. Có test
luồng auto Settings/Pin qua code intent/vision thật với API được mock, schema
chặn hành động đã bỏ, PNG không hợp lệ không gửi lên API, timeout không retry,
guard phần tử, xác minh và lưu bản ghi.

Kiểm tra WDA chỉ đọc, khi thiết bị đã kết nối:

```powershell
.\.venv\Scripts\python.exe scripts/wda_smoke.py
```

Test trên iPhone cần chủ động chạy CLI và thống nhất thao tác. Không tự thêm
thao tác thiết bị vào unittest. Sau thay đổi schema/API, test mock không thay
thế kiểm thử tương thích thực tế với dịch vụ/thiết bị.

## Quy tắc giữ repo gọn

- Mỗi module phải thuộc workflow chạy, test hoặc công cụ vận hành có mô tả.
- Không giữ bản sao CLI hoặc fallback cũ “để sau”; Git đã có lịch sử.
- Không thêm action vào schema nếu backend chưa hỗ trợ và chưa được kiểm chứng.
- Parser local và AI đều phải qua whitelist trong `direct.py` trước khi thao tác.
- Không retry thao tác khi timeout; tách API acknowledged với verified.
- Không commit key, identity, pairing, ảnh hoặc log cá nhân.

Đợt dọn repo đã bỏ CLI Voice Control/TTS, numbered vision, session cũ chưa track,
chụp DVT cũ và doctor USB không phản ánh tunnel hiện tại. Bộ kiểm tra PNG được
giữ trong vision; kiểm tra WDA dùng tunnel. Không xóa virtualenv, tool đã cài,
identity, provisioning hoặc bằng chứng local cần cho vận hành/đối chiếu.
