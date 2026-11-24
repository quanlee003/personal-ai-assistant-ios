# Trợ lý AI điều khiển iPhone bằng tiếng Việt

Bạn nói vào microphone của PC Windows → trợ lý hiểu yêu cầu → gửi thao tác trực
tiếp đến iPhone qua WebDriverAgent (WDA) → chụp màn hình để AI xác minh kết quả.
Chế độ tự động không yêu cầu Enter, sửa câu hay xác nhận `y` từng lượt.

**Bản hiện tại hỗ trợ mở app đã cài theo tên và mở phần Pin trong Cài đặt.**
Ví dụ: “mở Zalo”, “mở Safari”, “mở Đồng hồ”. Chỉ mở app, chưa thao tác bên trong
app khác ngoài chuyển tab/quay lại có giới hạn mô tả bên dưới; chưa tự lập kế hoạch nhiều bước. Tác vụ Pin không đổi tùy chọn. Đây là bản thử nghiệm
dùng PC kết nối iPhone, chưa phải ứng dụng độc lập cài từ App Store.

## 1. Dùng ngay trên máy đã thiết lập

### Mở cửa sổ Windows

**Chuyển tab bằng giọng nói:** mở Đồng hồ trên iPhone, bấm **Bắt đầu**, rồi nói
“chuyển sang Bấm giờ”, “chuyển sang Báo thức”, “chuyển sang Hẹn giờ” hoặc
“chuyển sang Giờ quốc tế”. Cũng nhận yêu cầu tiếng Anh như “switch to Stopwatch”.
Không cần bấm Đọc màn hình trước: mỗi lệnh tự đọc giao diện hiện tại để tìm tab.
App chỉ bấm một lần rồi kiểm tra tab được chọn; tab đã mở thì không bấm lại.
Không tạo/sửa báo thức hoặc chạy bộ đếm. Nếu không thấy tab phù hợp,
hoặc chưa xác minh được kết quả, app dừng và không tự gửi lại lần bấm.
Thao tác này dùng cấu trúc giao diện local, không chụp/gửi ảnh; giọng nói và câu
yêu cầu vẫn dùng Deepgram/AI Gateway như các lệnh mở app.

**Tab trong app khác:** nói “chuyển sang tab Tìm kiếm” hoặc “switch to tab Search”,
dùng đúng tên tab đang hiển thị. App đối chiếu tên trong thanh tab native iOS,
không bấm nút bất kỳ có cùng chữ và không tự mở ứng dụng khác. Tên tab Đồng hồ
vẫn có alias Việt/Anh; các tab khác chưa tự dịch tên. Tab vẽ tùy biến/WebView
có thể chưa được nhận diện; không có bảo đảm hỗ trợ mọi app.

**Quay lại:** nói “quay lại” hoặc “go back”. Hiện chỉ bấm khi có đúng một nút
Back/Quay lại/Trở lại hoặc định danh `BackButton` trong thanh điều hướng native.
Định danh này hỗ trợ nút mang nhãn trang trước như “Cài đặt” trên trang Pin.
Nếu không có nhãn/định danh trên, app không đoán từ icon hoặc nút Đóng. App kiểm tra tiêu đề
trang thay đổi trong cùng ứng dụng sau một lần bấm; đây là bằng chứng điều
hướng, không xác nhận nội dung cụ thể của trang đích. Nếu tiêu đề không đổi,
kết quả là chưa xác minh và app không bấm lại. Chưa hỗ trợ vuốt quay lại.

**Cuộn:** nói “cuộn xuống”, “cuộn lên”, “scroll down” hoặc “scroll up”. Mỗi yêu
cầu cuộn một lần trong app đang mở, không cần đọc màn hình trước. App yêu cầu
đúng một vùng cuộn native có đủ phần tử để kiểm tra; trang có nhiều vùng cuộn,
WebView hoặc giao diện tùy biến có thể chưa được hỗ trợ. Sau cuộn, ít nhất hai
phần tử phải dịch chuyển đúng chiều để xác minh. Ở đầu/cuối trang hoặc khi không
đủ bằng chứng, app báo chưa xác minh và không tự cuộn tiếp. Không hỗ trợ cuộn
đến mục cụ thể, cuộn hết trang, vuốt ngang hoặc chuỗi nhiều thao tác. Không gửi
ảnh/nội dung giao diện lên AI cho thao tác cuộn.

Sau khi cập nhật code, đóng và mở lại cửa sổ PC để nạp lệnh mới.

**Mở mục trên màn hình hiện tại:** nói “mở mục [tên]” hoặc “open section [name]”,
ví dụ “mở mục Music” trên trang có mục Music của App Store. App đọc các mục đang
hiển thị trong danh sách native, gửi tên/loại/ID tạm của các mục đủ điều kiện
tới AI Gateway để chọn một mục rồi kiểm tra lại giao diện trước một lần bấm.
Không tự mở app hoặc cuộn tìm mục. Lệnh Pin cũ vẫn dùng quy trình riêng đã có.

Chỉ dùng để mở trang xem nội dung. Bộ lọc loại nút thay đổi dữ liệu, ô nhập,
công tắc, thanh trượt, mục sát mép màn hình và các thao tác ngoài phạm vi;
AI từ chối khi không rõ đó là điều hướng. Nhãn giao diện không luôn mô tả đầy đủ
hành vi: đây vẫn là tính năng thử nghiệm, chưa bảo đảm mọi app. Kết quả chỉ
được xác minh khi tiêu đề trang mới khớp tên mục/yêu cầu trong cùng app; thiếu
tiêu đề hoặc tên khác thì báo chưa xác minh, không bấm lại.

Lệnh này gửi **tên mục giao diện** lên AI, có thể chứa thông tin riêng tư;
không gửi ảnh, giá trị ô nhập hoặc toàn bộ XML. Tùy chọn gửi ảnh của nút Đọc
màn hình không điều khiển bước chọn mục này. Khi có ô mật khẩu, hộp thoại,
sheet hoặc bàn phím hiển thị, không chọn mục phía sau. Phiên giọng nói tự động
không hỏi xác nhận từng lượt.

Nếu nút chỉ có mã nội bộ nhưng chứa đúng một nhãn chữ hiển thị, app dùng nhãn
con để hiểu yêu cầu và kết hợp mã nút với nhãn con để định vị. Nút có nhiều nhãn
con nhưng thiếu nhãn riêng vẫn bị bỏ qua. Tiêu đề trang ưu tiên chữ hiển thị
duy nhất trong thanh điều hướng thay vì mã nội bộ của thanh.

**Đọc màn hình:** mở trang muốn xem trên iPhone, giữ màn hình sáng rồi bấm
**Đọc màn hình** ở cột kết quả. App hiển thị tên ứng dụng, tiêu đề trang nếu có,
nội dung và các nút/ô nhập mà WDA đọc được. Chức năng này chỉ quan sát, chưa
bấm nút hoặc thực hiện tác vụ bên trong app. Không cần microphone hay key để đọc local.

Mặc định không chụp/gửi ảnh. Tích **Gửi ảnh tới AI Gateway để mô tả** trước khi
đọc nếu muốn AI bổ sung mô tả từ ảnh; mô tả có thể sai. Khi phát hiện ô mật khẩu,
app bỏ qua chụp/gửi ảnh. Đây không phải bộ lọc mọi thông tin riêng tư: chỉ bật
gửi ảnh khi bạn muốn chia sẻ nội dung màn hình với dịch vụ AI đã cấu hình.

Bản đọc nằm trong `runtime/screen-reads/`, mở bằng **Mở kết quả local**. Ảnh chỉ
được lưu khi chọn AI. App không tự đọc khi kết nối; nếu màn hình đổi trong lúc
đọc, app yêu cầu thử lại để tránh trộn nội dung. Trang động có thể cần tạm dừng
nội dung trước khi đọc. Một số app không cung cấp đầy đủ cấu trúc giao diện;
danh sách nhìn thấy không chứng minh mọi nút đều thao tác được.

**Quét máy trong app:** mở **Ứng dụng & thiết lập** ở cột trái. Khi app mở hoặc
phát hiện iPhone USB mới, app tự đọc danh sách ứng dụng. Khi đang rảnh, app kiểm
tra kết nối khoảng 12 giây/lần; không quét chen vào phiên giọng nói. Dùng **Quét
lại** sau khi cài/gỡ ứng dụng. Có thể tìm theo tên hoặc bundle ID. Mục System gồm
cả thành phần nội bộ, không đồng nghĩa tất cả đều có icon trên màn hình chính.

Tab **Điều kiện & quyền** chỉ rõ USB/Tin cậy cho quét, WDA cho điều khiển và
Thời gian sử dụng tùy chọn. Nút **Mở Thời gian sử dụng trên iPhone** điều hướng
bằng WDA khi kết nối sẵn sàng; không tự bật tính năng hay bấm đồng ý cấp quyền.
Nếu không mở được, app hiển thị đường dẫn để người dùng vào thủ công.

Danh mục lưu riêng theo mã thiết bị băm tại `runtime/device-profiles/`, chỉ ở
máy local. Khi mở app theo tên, chương trình đọc lại danh mục để kiểm tra app
còn trên đúng máy. Bản này chưa đọc báo cáo sử dụng và không gửi danh mục lên AI.

AI chỉ lấy tên app từ câu nói; chương trình đối chiếu local, không đoán bundle
ID. Tên không khớp hoặc trùng nhiều app sẽ không mở. App người dùng được hỗ trợ;
app hệ thống chỉ gồm danh sách app công khai trong `app_launch.py`, không mở các
dịch vụ nội bộ. Một số app hệ thống có tên Việt/Anh tương đương như Đồng hồ/Clock.
Danh mục quét vì thế rộng hơn danh sách app cho phép mở.

Mở app thông thường xác minh bằng bundle ID ở phía trước, không chụp/gửi ảnh
màn hình. Bản ghi có `verification_method=foreground_bundle`, bundle đích và
bundle quan sát. Điều này xác nhận app được mở, không xác nhận đăng nhập hoặc
nội dung đã tải xong. Cài đặt/Pin vẫn dùng luồng xác minh ảnh hiện có.

Trên máy đã thiết lập, app tự dùng môi trường thiết bị hiện có. Khi cài mới,
dependency cho quét thuộc extra `device` (`pip install -e ".[device]"`). Không
cần người dùng chạy một script quét riêng.

Nhấp đúp **`start-desktop.cmd`** trong thư mục project. Hoặc chạy:

```powershell
.\.venv\Scripts\pythonw.exe -m iphone_assistant.desktop
```

1. Kết nối USB, mở khóa iPhone và khởi chạy WDA như phần thiết lập bên dưới.
2. Cửa sổ tự kiểm tra iPhone, microphone mặc định và cấu hình dịch vụ. Việc kiểm
   tra chưa thu âm; “Đã cấu hình” chỉ xác nhận có key, chưa xác thực key qua mạng.
3. Khi sẵn sàng, chọn số lượt (mặc định 1), bấm **Bắt đầu**. Đợi **Đang nghe**
   rồi nói “mở Cài đặt” hoặc “mở phần Pin trong Cài đặt”. Không cần xác nhận lại.
4. Theo dõi nhận dạng, hiểu câu, thao tác và xác minh. Kết quả hiện bên phải;
   **Mở kết quả local** mở thư mục bản ghi JSON của lượt gần nhất.
5. Bấm **Dừng** để chặn bước tiếp theo. Lệnh đã gửi không thể thu hồi; cửa sổ
   chờ yêu cầu đang chạy trả về hoặc hết timeout, rồi đóng microphone/phiên.
   Đóng cửa sổ khi đang chạy cũng chờ dừng an toàn. Không mở phiên khác để thử lại
   trong lúc đang chờ. Nếu chưa xác định kết quả, kiểm tra iPhone trước khi chạy lại.

Audio gửi Deepgram; câu và ảnh sau thao tác gửi AI Gateway hiện có. Giao diện
không tự cài, ký lại hay khởi động WDA. Chưa có installer; cần môi trường `.venv`
đã cài project. Luồng terminal dưới đây vẫn dùng được.

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
.\.venv\Scripts\python.exe -c "from iphone_assistant.wda import WDABackend; print(WDABackend().ready())"
```

Thấy `True` thì có thể bắt đầu. Lệnh này chỉ đọc trạng thái, không
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
| `verified_match` | Xác nhận đúng bundle ID ở phía trước khi mở app; với Cài đặt/Pin, AI xác minh ảnh sau. |
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

## 5. Kết nối WDA

Các script thiết lập WDA đã được xóa khỏi repository. App hiện kiểm tra WDA
đang chạy; chưa tự cài, ký hoặc khởi động lại WDA. Quét danh sách app qua USB
vẫn hoạt động độc lập với WDA. Các script setup cũ không còn thuộc bản này.

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
Phần cài WDA và công cụ thiết bị hiện vẫn cần chuẩn bị riêng. Trên máy đã thiết
lập không cần cài lại mỗi lần dùng.

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
| GUI đã có Bắt đầu/Dừng và quét app | Bổ sung bộ cài và thiết lập lần đầu. |
| Ngưỡng âm lượng cố định | Chọn microphone, đo thử âm thanh, phát hiện hết câu ổn định trong tiếng ồn. |
| Kết quả hiển thị trong GUI | Bổ sung phản hồi bằng giọng nói; tránh thu lại tiếng trợ lý. |
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
- 131 tests đạt; test thông thường không tác động iPhone hoặc gọi cloud.
- Luồng AI chọn mục trên máy thật đã mở Pin trong Cài đặt và Music trong App
  Store, xác minh bằng tiêu đề đích. Màn hình Tệp đã thử không có mục đủ điều
  kiện nên không thao tác. Một lần bấm Cài đặt chung chưa chuyển trang và được
  báo chưa xác minh; sau đó bổ sung bộ lọc mục sát mép. Chưa kiểm thử microphone
  cho các ca mới ngoài xác nhận người dùng bên dưới; chưa suy rộng sang mọi app/màn hình.
- Người dùng xác nhận lệnh mở mục ban đầu hoạt động bằng giọng nói.
- Mở rộng kiểm thử 24/11/2026: Zalo chuyển tab Cá nhân thành công; sau cải tiến
  nhãn con và tiêu đề, AI mở Tài khoản và bảo mật đạt `verified_match`. Không
  đổi thiết lập tài khoản. Đây là ca gọi bằng code, chưa thử microphone cho Zalo.
- Messenger/Instagram/Spotify: đã quan sát màn hình mở đầu; chưa tìm được mục
  điều hướng công khai phù hợp trong ứng viên để thử click, không mở hội thoại
  hoặc phát nội dung. GitHub: màn hình đã thử không có ứng viên đủ điều kiện.
  YouTube: đã đọc ứng viên nhưng khi thử yêu cầu thì foreground đã về màn hình
  chính, nên lệnh bị chặn trước click. Các quan sát này không phải kết luận
  toàn bộ ứng dụng không được hỗ trợ.
- Dữ liệu Pin được đọc thủ công trong lượt kiểm thử để chọn nhóm app ưu tiên;
  chưa có tính năng tự thu thập/xếp hạng thói quen từ Pin trong app PC. Không
  coi phần trăm pin hoặc thời gian chạy nền là thời gian người dùng tương tác.
- Người dùng xác nhận giọng nói chuyển tab App Store và quay lại đã thành công.
- Đã thử cuộn xuống rồi lên trong Cài đặt trên iPhone thật: cả hai lượt đạt
  `verified_match` bằng `visible_element_movement`, mỗi lượt gửi đúng một lần
  cuộn và nhận phản hồi. Kiểm thử gọi bằng code; chưa thử microphone cho lệnh
  cuộn và chưa suy rộng sang app khác.
- Mở rộng tab theo tên và quay lại đã qua kiểm thử tự động; AI Gateway thực tế
  nhận đúng “switch to tab Search” và “go back”. Trên iPhone thật đã xác minh
  chuyển sang Bấm giờ trong Đồng hồ, Tìm kiếm/Today trong App Store và quay lại
  từ Pin về Cài đặt. Các lượt mới này gọi bằng code, chưa kiểm thử microphone
  cho tab App Store và lệnh quay lại; không suy rộng thành hỗ trợ mọi app.
- Đã đọc local màn hình Đồng hồ / Báo thức trên iPhone thật, nhận diện 13 thành
  phần giao diện. Phần mô tả bằng AI được kiểm thử bằng mock, chưa thử cloud thực tế.
- Đã kiểm thử chuyển cả bốn tab Đồng hồ trên iPhone thật: mỗi
  chuyển tab bấm đúng một lần và xác minh `selected_tab`. Gọi lại tab Hẹn giờ
  đang mở không phát lần bấm mới. Kiểm thử này dùng lệnh văn bản qua luồng app,
  người dùng sau đó xác nhận lệnh giọng nói chuyển tab hoạt động trên máy mình.
- Đã thử yêu cầu gõ qua AI → đối chiếu danh mục → mở Đồng hồ, Safari và Zalo trên máy thật, đều xác minh đúng app.
- Ngày 24/11/2026, người dùng xác nhận đã thử tính năng mở app và hoạt động ổn định trên máy của mình; chưa suy rộng sang mọi app hoặc thiết bị khác.
- Chưa kiểm chứng app khác, máy/thiết bị khác hoặc phục hồi sau reboot đầy đủ.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Module chính: `direct_cli.py` điều phối; `endpoint.py` kết thúc thu; `speech.py`
nhận dạng; `intent.py` hiểu yêu cầu; `direct.py` giới hạn thực thi và trả kết quả;
`wda.py` kết nối thiết bị; `verification.py` đánh giá ảnh.

- [Kiến trúc hiện tại và ranh giới module](docs/architecture.md).
- [Hướng dẫn phát triển và kiểm tra repo](docs/development.md).
- Cảm hứng kiến trúc: [WhisperTest](https://github.com/iOSWhisperTest/whispertest).
  Project phát triển độc lập; tái sử dụng code về sau cần giữ giấy phép/thông báo tương ứng.
