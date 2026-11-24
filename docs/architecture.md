# Kiến trúc hiện tại

Ứng dụng PC điều phối iPhone qua WDA: mở app theo tên và mở trang Pin.
Mỗi lượt nhận yêu cầu mới; không có planner tổng quát, TTS hay Voice Control fallback.

## Luồng chạy

```text
desktop (Tk main thread) → desktop_controller (một worker, Queue, stop Event)
                            └─ direct_cli.run_logged_turn
direct_cli (auto hoặc debug)
  ├─ endpoint → speech: thu âm/Deepgram (khi dùng microphone)
  ├─ intent → commands: AI Gateway tạo lệnh (hoặc parser local)
  ├─ direct: kiểm tra phạm vi, số bước, kết quả
  │    └─ wda: readiness, ảnh, mở Settings, tìm/kiểm tra/chạm nút Pin
  └─ verification → vision: đánh giá ảnh sau qua AI Gateway
```

| Module | Trách nhiệm |
| --- | --- |
| `desktop.py` | Cửa sổ Tkinter, trạng thái, nút Bắt đầu/Dừng và kết quả; không xử lý nền trên Tk thread. |
| `desktop_controller.py` | Kiểm tra điều kiện, một worker mỗi cửa sổ, giới hạn 1–10 lượt và sự kiện có cấu trúc. |
| `control.py` | Dừng hợp tác trước bước tiếp theo; không hủy cưỡng bức lệnh đang chạy. |
| `direct_cli.py` | Input/output, cấu hình `.env`, auto/debug, giới hạn lượt, JSON local. |
| `commands.py` | Kiểu Command, chuẩn hóa tiếng Việt, parser mở app/dừng. |
| `direct.py` | Parser Pin, whitelist tác vụ, ActionResult, quy trình tối đa hai bước. |
| `wda.py` | HTTP một lần qua tunnel loopback; chọn phần tử bằng identifier và kiểm tra lại trước click. |
| `screen_reader.py` | Đọc cấu trúc giao diện local; mô tả ảnh qua AI chỉ khi người dùng bật tùy chọn. |
| `screen_navigation.py` | Tìm tab hoặc nút Back native hiện tại; một lần bấm, kiểm tra lại cấu trúc và foreground, không retry. |
| `screen_scroll.py` | Một lần cuộn dọc; yêu cầu một vùng cuộn native và xác minh chuyển động của phần tử trong cùng app. |
| `screen_target.py` | Danh sách phần tử native đủ điều kiện → AI chọn ID tạm → kiểm tra lại phần tử/foreground → một click → xác minh tiêu đề đích. |
| `speech.py` | Thu thủ công trong debug, gửi WAV đến Deepgram. |
| `endpoint.py` | Thu auto, kết thúc theo âm lượng/im lặng, timeout và giới hạn thời lượng. |
| `intent.py` | Schema/validation và client AI Gateway: open_app, select_target, select_tab, go_back, scroll, open_item, stop. |
| `vision.py` | Kiểm tra PNG, gửi ảnh, kiểm tra schema và tính nhất quán của kết luận. |
| `verification.py` | Prompt đánh giá màn hình sau thao tác; không thao tác thiết bị. |

`DIRECT_PROMPT` nằm tại CLI và được truyền rõ cho intent. Prompt xác minh được
truyền từ verification sang vision. Không còn prompt mặc định cho khả năng cũ.
Schema intent giữ `direction="none"` để bảo toàn cấu trúc phản hồi hiện tại;
scroll đặt hướng up/down trong value, được chuyển thành arguments.direction;
không có thao tác vuốt ngang hoặc cuộn nhiều bước.

## Bộ thực thi

`app_launch.py` xử lý mở app ngoài Cài đặt: quét mới, đối chiếu chính xác tên đã
chuẩn hóa hoặc alias hệ thống được khai báo, từ chối tên trùng/không khớp và dịch
vụ hệ thống nội bộ. AI không nhận danh mục và không tự chọn bundle ID. Trước khi
mở, hash thiết bị phải khớp tunnel WDA. POST mở app chỉ gửi một lần; đọc foreground
tối đa bốn lần để xác minh. Không chụp hoặc gửi ảnh app khác lên vision.
Kết quả ghi bundle đích, bundle quan sát và phương pháp xác minh; timeout không retry.

- Mở Cài đặt: một lần tạo session với bundle `com.apple.Preferences`.
- Trang Pin: mở Cài đặt; nếu đã đúng trang Pin thì không chạm. Nếu chưa, tìm đúng
  một button có identifier `com.apple.settings.battery`, visible/enabled.
- Kiểm tra foreground, tên, loại, visible/enabled trước click; phần tử chỉ dùng
  một lần. Không cuộn hoặc đoán tọa độ khi không tìm thấy.
- Sau thao tác, chụp ảnh. Với Pin, kiểm tra tiêu đề navigation trước AI verify.
- Không retry thao tác hoặc cloud request. Timeout sau khi bắt đầu là kết quả
  chưa rõ, không được chuyển thành thành công hoặc tự gửi lại.

API trả lời chỉ là acknowledged. `verified_match` dựa trên phương pháp của tác vụ:
ảnh với Cài đặt/Pin, foreground bundle khi mở app, selected tab khi chuyển tab,
hoặc tiêu đề navigation thay đổi trong cùng app khi quay lại. Kiểm tra tiêu đề
không chứng minh nội dung trang đích. Điều hướng không gửi cấu trúc UI lên AI.
Ngoại lệ là `open_item`: gửi nhãn/loại/ID tạm của ứng viên đủ điều kiện lên AI
Gateway, không gửi XML/selector/ảnh/input value. Dùng lại schema intent với
select_target trả ID; ID chỉ có hiệu lực trong lượt đọc hiện tại. Phần tử cần
khớp fingerprint trước/sau AI và trước click, selector phải trả đúng một phần
tử, type/label/visible/enabled phải còn đúng. Chỉ báo verified_match khi tiêu đề
mới khác tiêu đề cũ và khớp nhãn mục hoặc yêu cầu. Bộ lọc local và đánh giá AI
giảm chọn nhầm hành động, không phải chứng minh ngữ nghĩa của mọi control.
Nếu nút thiếu label nhưng có đúng một StaticText hiển thị, dùng chữ con làm
nhãn ứng viên; XPath kết hợp name của nút và nhãn con, kiểm tra name/type thay
vì giả định label tồn tại. Không đưa mã nội bộ không có nhãn chữ lên AI.
NavigationBar ưu tiên đúng một StaticText hiển thị làm tiêu đề. Hộp thoại,
sheet, bàn phím hoặc ô mật khẩu hiển thị chặn toàn bộ chọn mục, kể cả khi WDA
vẫn đánh dấu các phần tử nền là visible. Kiểm tra lại sau AI vẫn áp dụng guard.
Tab chỉ lấy button trong TabBar; Back nhận nhãn Back/Quay lại/Trở lại hoặc
định danh BackButton trong NavigationBar. Không suy đoán từ tọa độ, nút Đóng
hoặc tên trang trước khi thiếu định danh BackButton. XPath
escape tên quan sát được, không chèn trực tiếp yêu cầu model vào selector.
`steps_attempted` đếm bước đã bắt đầu, kể cả bị guard chặn trước khi gửi;
`steps_acknowledged` đếm bước được WDA phản hồi. Không suy ra toàn bộ quy trình
thành công chỉ từ `action_acknowledged=true`.

## Dữ liệu và vòng đời

Mỗi lượt có JSON riêng ở `runtime/direct-results/`. Bản ghi incomplete được tạo
trước xử lý; kết quả cuối thay thế qua file tạm. Ảnh ở `captures/`; không lưu
riêng audio/transcript, nhưng message AI có thể chứa nội dung màn hình/lời nói.
Microphone đóng trong lúc xử lý cloud/device. Nói dừng chỉ có tác dụng khi đang
nghe; Ctrl+C dùng để ngắt CLI ngoài giai đoạn thu. CLI mặc định tối đa 10 lượt;
giao diện mặc định 1 lượt. Nút Dừng và đóng cửa sổ chờ request đang chạy kết thúc,
không khởi chạy lại. Chỉ mở một cửa sổ để dùng với iPhone; khóa worker có phạm vi
mỗi cửa sổ, chưa phải khóa liên tiến trình.

Cloud: Deepgram nova-3 tiếng Việt; AI Gateway dùng Gemini flash-lite cho intent
và flash cho vision theo `.env`. Không có cơ chế phân phối key cho người dùng cuối.
Ảnh/log, tool, virtualenv, `.env` và identity được Git ignore.

## Công cụ vận hành

Các script setup cũ đã được xóa khỏi repo. App kiểm tra WDA có sẵn, chưa tự thiết lập runtime.

Quét nằm trong app chính: `device_catalog` gọi worker nội bộ `device_probe` bằng
môi trường thiết bị để tách dependency USB khỏi môi trường voice. Worker chỉ
đọc; output có cấu trúc, không xuất serial thô. Catalog được lưu theo hash thiết
bị. Controller dùng chung khóa worker cho voice/quét/setup, không thao tác chồng.
`phone_setup` chỉ điều hướng hữu hạn đến Screen Time khi người dùng bấm nút,
đối chiếu identity với tunnel, không bật quyền. Xem [quyền iOS](ios-permissions.md).

Giao diện PC tái sử dụng ActionResult và sự kiện có cấu trúc, không phân tích
dòng print. Kiểm tra ban đầu chỉ đọc WDA và cấu hình microphone/key, chưa thu âm
hoặc xác thực key qua mạng. Không khôi phục các CLI TTS cũ.
