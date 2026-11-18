# Trợ lý AI điều khiển iPhone bằng tiếng Việt

Bạn nói vào microphone của PC Windows → trợ lý hiểu yêu cầu → gửi thao tác trực
tiếp đến iPhone qua WebDriverAgent (WDA) → chụp màn hình để AI xác minh kết quả.
Chế độ tự động không yêu cầu Enter, sửa câu hay xác nhận `y` từng lượt.

**Bản hiện tại hỗ trợ “mở Cài đặt” và “mở phần Pin trong Cài đặt”.** Tác vụ Pin
chỉ mở trang để xem, không đổi tùy chọn. Chưa điều khiển app khác hoặc tự lập kế
hoạch nhiều bước. Đây là bản thử nghiệm
dùng PC kết nối iPhone, chưa phải ứng dụng độc lập cài từ App Store.

## 1. Dùng ngay trên máy đã thiết lập

Các lệnh dưới đây chạy trong **PowerShell**. Máy hiện tại đã có công cụ và cấu
hình; không cần cài lại mỗi lần. Lệnh gọi thẳng Python của project nên không cần
kích hoạt virtualenv.

### Chuẩn bị

1. Kết nối đúng một iPhone bằng USB và mở khóa thiết bị.
2. Cắm microphone/tai nghe, chọn đúng đầu vào mặc định của Windows. Lần kiểm tra
   trước dùng EarPods; chương trình không cố định vào EarPods.
3. Có Internet để dùng Deepgram và AI Gateway.
4. Mở terminal tại project:

```powershell
Set-Location C:\personal-ai-assistant-ios
```

### Kiểm tra kết nối

```powershell
.\.venv\Scripts\python.exe scripts/wda_smoke.py
```

Thấy `"wda_ready": true` thì có thể bắt đầu. Lệnh này chỉ đọc trạng thái, không
mở app hoặc chụp ảnh. Nếu lỗi, xem mục **Khôi phục kết nối** bên dưới.

### Bắt đầu nói, không cần xác nhận

Thử một lượt trước:

```powershell
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli --auto --max-turns 1
```

Khi hiện **“Đang nghe…”**, nói **“mở Cài đặt”**, rồi ngừng nói khoảng 1,2 giây.
Chương trình tự kết thúc thu, hiểu yêu cầu, mở Cài đặt và đánh giá ảnh. Không cần
nhấn Enter hoặc nhập `y`.

Có thể nói **“mở phần Pin trong Cài đặt”**: trợ lý mở Cài đặt, tìm đúng một nút Pin
đang hiển thị và chạm một lần, rồi xác minh trang Pin. Nếu đã ở trang Pin thì không
chạm thêm. Nếu không thấy đúng mục tiêu, phiên dừng; chưa tự cuộn hoặc quay lại
trang chính từ một trang con khác. Không thao tác iPhone bằng tay trong lúc chạy.
Hai lượt auto mở trang Pin đã chạy end-to-end và được AI xác minh thành công.

Muốn chạy tối đa hai lượt liên tiếp:

```powershell
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli --auto --max-turns 2
```

Sau lượt thành công, chương trình tự nghe lượt kế tiếp. Chờ “Đang nghe” rồi mới
nói. Bỏ `--max-turns` thì mặc định tối đa 10 lượt. **Đây không phải chế độ nghe
nền vô thời hạn.** Nếu không định nói thêm, dùng một lượt hoặc dừng phiên.

### Dừng

- **Ctrl+C** trong terminal để ngắt, kể cả lúc chờ AI/WDA.
- Khi đang nghe, nói **“dừng”** hoặc **“thoát”**; chương trình nhận dạng rồi đóng phiên.
- Khi AI/WDA xử lý, microphone đã đóng nên không nhận lệnh dừng bằng giọng nói.

Dừng phiên không hoàn tác lệnh đã gửi. Nếu thao tác đã bắt đầu mà chưa rõ kết
quả, kiểm tra màn hình trước khi chạy lại. Đóng CLI không tự dừng tunnel/WDA.

## 2. Một lượt thực sự làm gì?

```text
Microphone PC → kết thúc khi im lặng → Deepgram nhận dạng tiếng Việt
  → AI Gateway hiểu yêu cầu → kiểm tra phạm vi cho phép
  → WDA chụp ảnh trước → mở Cài đặt → chụp ảnh sau
  → AI Gateway đánh giá ảnh sau → lưu kết quả → nghe lượt mới hoặc dừng
```

WDA là bộ thực thi duy nhất. Code Voice Control/TTS và các CLI cũ đã được loại
bỏ; khi WDA lỗi, phiên dừng. Chế độ debug trong README dùng cùng backend direct.

Câu không rõ: hiện câu hỏi trên terminal, nghe yêu cầu mới nếu còn lượt, không
tái dùng mục tiêu cũ. Chưa có phản hồi bằng giọng nói; vẫn cần nhìn trạng thái
trên terminal. Tác vụ Pin là quy trình cố định tối đa hai bước, chưa phải planner tự do.

## 3. Đọc kết quả và tìm bản ghi

| Trạng thái | Ý nghĩa |
| --- | --- |
| `verified_match` | AI thấy ảnh sau phù hợp với màn hình mong đợi. |
| `action_sent` | WDA đã phản hồi nhưng chưa đánh giá kết quả bằng ảnh. |
| `needs_clarification` | Câu chưa rõ hoặc chưa hỗ trợ; không thao tác. |
| `target_not_found` | Mục tiêu ngoài phạm vi hoặc không tìm thấy nút Pin hợp lệ. Có thể đã mở Cài đặt; xem các cờ/bộ đếm bước. |
| `verified_mismatch` | Ảnh sau không phù hợp; phiên dừng. |
| `verification_uncertain` | Chưa đủ bằng chứng, bỏ qua xác minh hoặc lỗi sau khi bắt đầu thao tác; phiên dừng. |
| `error` | Lượt xử lý lỗi; cần đối chiếu cờ thao tác, không suy ra thiết bị đã thay đổi. |
| `canceled` | Đã hủy/dừng phiên. |
| `dry_run` | Chỉ xem trước, chưa thực thi. |
| `incomplete` | Chưa có kết quả cuối; không kết luận đã hay chưa thao tác. |

Đánh giá AI không phải bảo đảm tuyệt đối. Đối chiếu thêm `action_attempted`,
`action_acknowledged` và ảnh khi điều tra lỗi.

- JSON: `runtime/direct-results/<id>/result.json`, gồm chế độ `auto`/`debug`,
  thời gian UTC, trạng thái, thông báo và đường dẫn ảnh nếu có.
- `steps_attempted`/`steps_acknowledged`: số bước bắt đầu/được phản hồi; một bước
  có thể bị chặn lúc kiểm tra trước khi gửi. `error_code` giúp phân loại lỗi.
- Ảnh: `captures/direct-<id>/before.png` và `after.png`.
- Các thư mục này được Git ignore; chưa có cơ chế tự dọn theo thời hạn.

Đọc kết quả mới nhất:

```powershell
Get-ChildItem .\runtime\direct-results\*\result.json |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 |
    Get-Content -Encoding UTF8
```

## 4. Khi không nhận đúng lời nói

| Hiện tượng | Cách xử lý hiện tại |
| --- | --- |
| `no_speech` | Chưa thu đủ lời nói trong 8 giây; kiểm tra microphone và nói khi hiện “Đang nghe”. Chưa gửi audio. |
| `too_long` | Thu đạt 20 giây; nói câu ngắn hơn, giảm tiếng nền. Bản thu bị cắt không được gửi. |
| `audio_error` / `audio_timeout` / `audio_capture_error` | Lỗi/cảnh báo hoặc timeout microphone; kiểm tra đầu vào và quyền microphone. Chưa gửi audio. |
| `transcription_error` | Audio đã qua bước thu nhưng nhận dạng Deepgram lỗi; kiểm tra Internet/key/quota. Chưa thao tác iPhone. |
| Nhận sai câu | Nói câu ngắn, rõ, gần microphone. Auto không bắt gõ sửa; nói lại ở lượt nghe mới. |
| Ngừng giữa câu làm kết thúc sớm | Tăng khoảng im lặng, ví dụ `--silence-seconds 1.8`. |
| Tiếng nền khiến thu mãi | Giảm tiếng nền; có thể tăng `--voice-threshold`. Quá cao sẽ bỏ sót giọng nhỏ. |
| Lỗi sau khi gửi thao tác | Xem màn hình/ảnh và JSON trước khi chạy lại để tránh lặp thao tác chưa rõ kết quả. |

Các bản ghi cũ chỉ có `SpeechInputError` chưa thể phân loại lại chỉ từ dữ liệu đã lưu.

```powershell
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli --auto --max-turns 1 --silence-seconds 1.8
```

Bộ phát hiện hiện dựa trên mức âm lượng RMS và khoảng im lặng, chưa phân biệt
giọng nói/tiếng ồn chuyên dụng. Ngưỡng mặc định 500, im lặng 1,2 giây.
`--voice-threshold` nhận 1–32767; `--silence-seconds` nhận 0,5–3.
Trong 8 giây không thu đủ tiếng vượt ngưỡng hoặc bản thu đạt 20 giây, phiên dừng
và không gửi bản thu đó. Vì vậy, im lặng ở lượt hai có thể làm phiên kết thúc
bằng lỗi dù lượt đầu thành công.

## 5. Khôi phục kết nối

**WDA đã ready thì bỏ qua mục này.** Những lệnh sau dùng setup có sẵn trên máy
hiện tại, không phải trình cài cho máy mới. Cần USB/pairing, Developer Mode,
runner đã ký và DDI phù hợp. Chuỗi khôi phục sau reboot chưa được kiểm thử đầy đủ.

Chạy từng lệnh, xem kết quả rồi mới tiếp tục:

```powershell
# 1. Khởi động tunnel nếu chưa có
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/start_direct.py tunnel

# 2. Kiểm tra DDI/dịch vụ XCTest
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/ddi_userspace.py

# 3. Khi DDI và dịch vụ XCTest đã sẵn sàng, khởi động runner
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/start_direct.py wda

# 4. Chỉ dùng trợ lý khi ready=true
.\.venv\Scripts\python.exe scripts/wda_smoke.py
```

“Started process” chỉ xác nhận tạo tiến trình, chưa xác nhận sẵn sàng. Nếu báo
tunnel/PID còn chạy, không khởi động chồng hoặc tự xóa PID; kiểm tra tiến trình
và log ở `artifacts/direct-setup/`.

Nếu thiếu DDI, xem [hướng dẫn runtime](docs/direct-windows.md#runtime).
`ddi_userspace.py --mount` có thể gửi dữ liệu personalization tới Apple và mount
DDI, không phải lệnh chỉ đọc. Profile ký WDA hết hạn thì cần ký/cài lại bằng
Sideloadly và kiểm tra Trust trên iPhone; chưa có gia hạn tự động.

## 6. Debug khi cần tìm lỗi

Trải nghiệm thông thường là `--auto`. Chế độ debug giữ sửa câu và xác nhận:

```powershell
# Preview offline, không microphone/cloud/thao tác iPhone
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli "mở Cài đặt"

# Xác nhận thực thi, ảnh local, chưa có AI xác minh
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli "mở Cài đặt" --execute

# Giọng nói, sửa câu, xác nhận từng giai đoạn
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli --listen --ai --execute --verify
```

Debug giọng nói: Enter bắt đầu/kết thúc thu → Enter giữ câu hoặc gõ cả câu để
sửa → `y` gửi AI → `y` thực thi → `y` gửi ảnh xác minh. `/cancel` ở bước sửa câu
để dừng. Thêm `--session` để chạy nhiều lượt; `/quit` ở đầu lượt để thoát.

## 7. Cài đặt và dữ liệu

### Máy mới

Cần Windows/Python, USB/iPhone, microphone, Internet, key Deepgram/AI Gateway,
WDA được ký/provisioning cho thiết bị, Trust/Developer Mode/pairing, go-ios và DDI.
Repository chưa có bộ cài hoàn chỉnh. Clone code không mang theo virtualenv,
runner đã ký, công cụ tải về hoặc cấu hình private.

Phần dependency ứng dụng với Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Lệnh này **chỉ cài ứng dụng Python**, chưa thiết lập WDA/USB/DDI. Dependency chính
gồm sounddevice, python-dotenv, openai và pydantic; không còn extra/dependency TTS.
Xem [setup Windows đã kiểm chứng](docs/direct-windows.md)
để biết công cụ/phiên bản và các bước thiết bị. Trên máy hiện tại không cần cài lại.

Tạo `.env` tại thư mục project bằng key của bạn; không đưa key thật vào Git:

```dotenv
DEEPGRAM_API_KEY=<key của bạn>
AI_GATEWAY_API_KEY=<key của bạn>
AI_GATEWAY_MODEL=google/gemini-2.5-flash-lite
AI_GATEWAY_VISION_MODEL=google/gemini-2.5-flash
```

### Dữ liệu đi đâu?

| Dữ liệu | Nơi sử dụng |
| --- | --- |
| Audio thu thành công | Deepgram để nhận dạng; auto hiện không ghi audio thành file. |
| Câu nhận dạng/yêu cầu | AI Gateway để hiểu ý định; debug cần đồng ý gửi. |
| Ảnh trước | Lưu local để đối chiếu. |
| Ảnh sau | Lưu local và gửi AI Gateway khi xác minh; auto gửi không hỏi lại. |
| JSON kết quả | Lưu local; thông báo AI có thể nhắc lại lời nói/nội dung màn hình. |

Auto không hoàn toàn offline. Các API sử dụng quota/chi phí theo tài khoản đang
cấu hình; ứng dụng chưa giới hạn chi phí. Ảnh được lưu local không có nghĩa ảnh
chưa được gửi cloud. Không lưu riêng transcript nhưng thông báo kết quả có thể
chứa nội dung của nó.

## 8. Nếu phát triển thành sản phẩm, cần tối giản gì?

**Trải nghiệm mục tiêu đề xuất:** mở ứng dụng PC → thấy “iPhone đã kết nối” →
bấm “Bắt đầu” → nói yêu cầu → nhận phản hồi. Người dùng không cần terminal,
nhớ lệnh, biết WDA/DDI hoặc xác nhận lại các thao tác thông thường đã hỗ trợ.

Các mục sau là hướng phát triển, **chưa phải tính năng hiện có**:

| Hiện tại | Cần đơn giản hóa |
| --- | --- |
| Tự kiểm tra/start tunnel và WDA | Tự kiểm tra kết nối, khởi động thành phần cần thiết, báo lỗi dễ hiểu. |
| Ký runner, Trust, DDI qua nhiều công cụ | Hướng dẫn thiết lập lần đầu, theo dõi provisioning và khôi phục kết nối. Khả năng phân phối rộng còn phải kiểm chứng riêng. |
| Chạy câu lệnh Python | Giao diện Bắt đầu/Dừng, trạng thái Nghe/Đang xử lý/Hoàn tất. |
| Ngưỡng âm lượng cố định | Chọn microphone, đo thử âm thanh, phát hiện hết câu ổn định trong tiếng ồn. |
| Chỉ phản hồi terminal | Phản hồi dễ hiểu, hỏi lại bằng giọng nói; tránh thu lại tiếng trợ lý. |
| Người dùng tự chuẩn bị key | Thiết kế đăng nhập, lưu secret, quota và chi phí rõ ràng. |
| Mở Cài đặt/trang Pin qua quy trình cố định | Mở rộng từng tác vụ đã kiểm chứng: nhận diện phần tử, thực thi, xác minh. |
| Ảnh/JSON tích lũy trong thư mục | Lịch sử dễ đọc, thời hạn lưu/xóa và quyền chia sẻ dữ liệu minh bạch. |

Thứ tự đề xuất: **ổn định kết nối/audio → giao diện một nút → mở rộng tác vụ**.
Chưa cần gộp wake word, nghe nền và agent tự chủ nhiều bước cùng một đợt.
Xác nhận riêng nên dành cho hành động nhạy cảm khi hỗ trợ những hành động đó.
Điều khiển được qua WDA chưa chứng minh có đường phát hành đại trà hoặc chạy
độc lập trên iPhone.

## 9. Trạng thái kiểm chứng và tài liệu kỹ thuật

Tính đến 18/11/2026:

- Một lượt auto thực tế đạt `verified_match`: giọng nói → AI → WDA → AI xác minh.
- Có câu không rõ được chặn trước thao tác; hai lượt auto lỗi audio/nhận dạng
  trước thao tác trong giai đoạn đầu. Chưa kiểm chứng độ ổn định trong tiếng ồn.
- Đã mở Cài đặt và chạm đúng nút Pin bằng identifier WDA; ảnh sau và tiêu đề điều
  hướng xác nhận trang Pin. Hai bản ghi auto mới nhất đều `verified_match`,
  `steps_attempted=2`, `steps_acknowledged=2`, `error_code=null`; người dùng xác
  nhận hoạt động tốt. Đã kiểm chứng giọng nói → AI → launch/click → AI xác minh.
  Không suy ra hai lượt thuộc cùng một phiên vì bản ghi chưa có session ID.
- Sau đợt dọn repo, 49 tests đạt; test thông thường không tác động iPhone hoặc gọi cloud.
- Chưa kiểm chứng app khác, máy/thiết bị khác hoặc phục hồi sau reboot đầy đủ.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Module chính: `direct_cli.py` điều phối; `endpoint.py` kết thúc thu; `speech.py`
nhận dạng; `intent.py` hiểu yêu cầu; `direct.py` giới hạn thực thi và trả kết quả;
`wda.py` kết nối thiết bị; `verification.py` đánh giá ảnh.

- [Thiết lập Windows, bằng chứng và nhật ký kỹ thuật](docs/direct-windows.md).
- [Kiến trúc hiện tại và ranh giới module](docs/architecture.md).
- [Hướng dẫn phát triển và kiểm tra repo](docs/development.md).
- Cảm hứng kiến trúc: [WhisperTest](https://github.com/iOSWhisperTest/whispertest).
  Project phát triển độc lập; tái sử dụng code về sau cần giữ giấy phép/thông báo tương ứng.
