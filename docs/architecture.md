# Kiến trúc hiện tại

Ứng dụng PC điều phối iPhone qua WDA. Chỉ có hai tác vụ: mở Cài đặt và mở trang Pin.
Mỗi lượt nhận yêu cầu mới; không có planner tổng quát, TTS hay Voice Control fallback.

## Luồng chạy

```text
direct_cli (auto hoặc debug)
  ├─ endpoint → speech: thu âm/Deepgram (khi dùng microphone)
  ├─ intent → commands: AI Gateway tạo lệnh (hoặc parser local)
  ├─ direct: kiểm tra phạm vi, số bước, kết quả
  │    └─ wda: readiness, ảnh, mở Settings, tìm/kiểm tra/chạm nút Pin
  └─ verification → vision: đánh giá ảnh sau qua AI Gateway
```

| Module | Trách nhiệm |
| --- | --- |
| `direct_cli.py` | Input/output, cấu hình `.env`, auto/debug, giới hạn lượt, JSON local. |
| `commands.py` | Kiểu Command, chuẩn hóa tiếng Việt, parser mở app/dừng. |
| `direct.py` | Parser Pin, whitelist tác vụ, ActionResult, quy trình tối đa hai bước. |
| `wda.py` | HTTP một lần qua tunnel loopback; chọn phần tử bằng identifier và kiểm tra lại trước click. |
| `speech.py` | Thu thủ công trong debug, gửi WAV đến Deepgram. |
| `endpoint.py` | Thu auto, kết thúc theo âm lượng/im lặng, timeout và giới hạn thời lượng. |
| `intent.py` | Schema/validation và client AI Gateway; chỉ open_app, select_target, stop. |
| `vision.py` | Kiểm tra PNG, gửi ảnh, kiểm tra schema và tính nhất quán của kết luận. |
| `verification.py` | Prompt đánh giá màn hình sau thao tác; không thao tác thiết bị. |

`DIRECT_PROMPT` nằm tại CLI và được truyền rõ cho intent. Prompt xác minh được
truyền từ verification sang vision. Không còn prompt mặc định cho khả năng cũ.
Schema intent giữ `direction="none"` để bảo toàn cấu trúc phản hồi hiện tại;
không có thao tác vuốt/hướng di chuyển.

## Bộ thực thi

- Mở Cài đặt: một lần tạo session với bundle `com.apple.Preferences`.
- Trang Pin: mở Cài đặt; nếu đã đúng trang Pin thì không chạm. Nếu chưa, tìm đúng
  một button có identifier `com.apple.settings.battery`, visible/enabled.
- Kiểm tra foreground, tên, loại, visible/enabled trước click; phần tử chỉ dùng
  một lần. Không cuộn hoặc đoán tọa độ khi không tìm thấy.
- Sau thao tác, chụp ảnh. Với Pin, kiểm tra tiêu đề navigation trước AI verify.
- Không retry thao tác hoặc cloud request. Timeout sau khi bắt đầu là kết quả
  chưa rõ, không được chuyển thành thành công hoặc tự gửi lại.

API trả lời chỉ là acknowledged. `verified_match` cần kết luận ảnh phù hợp.
`steps_attempted` đếm bước đã bắt đầu, kể cả bị guard chặn trước khi gửi;
`steps_acknowledged` đếm bước được WDA phản hồi. Không suy ra toàn bộ quy trình
thành công chỉ từ `action_acknowledged=true`.

## Dữ liệu và vòng đời

Mỗi lượt có JSON riêng ở `runtime/direct-results/`. Bản ghi incomplete được tạo
trước xử lý; kết quả cuối thay thế qua file tạm. Ảnh ở `captures/`; không lưu
riêng audio/transcript, nhưng message AI có thể chứa nội dung màn hình/lời nói.
Microphone đóng trong lúc xử lý cloud/device. Nói dừng chỉ có tác dụng khi đang
nghe; Ctrl+C dùng để ngắt ngoài giai đoạn thu. Mỗi lần chạy mặc định tối đa 10 lượt.

Cloud: Deepgram nova-3 tiếng Việt; AI Gateway dùng Gemini flash-lite cho intent
và flash cho vision theo `.env`. Không có cơ chế phân phối key cho người dùng cuối.
Ảnh/log, tool, virtualenv, `.env` và identity được Git ignore.

## Công cụ vận hành

`scripts/` chỉ giữ bốn công cụ cần cho setup/khôi phục/chẩn đoán:
`prepare_wda_ipa.py`, `start_direct.py`, `ddi_userspace.py`, `wda_smoke.py`.
Không import các script thiết lập vào vòng lặp tác vụ. Xem [setup Windows](direct-windows.md).

Giao diện PC chưa triển khai. Khi bổ sung, cần tái sử dụng kết quả có cấu trúc,
không phân tích dòng print để điều khiển logic. Không khôi phục các CLI TTS cũ.
