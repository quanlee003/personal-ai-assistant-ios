# Điều khiển trực tiếp trên Windows — milestone mở Cài đặt đã đạt

## Trạng thái mới nhất: phép thử trực tiếp đạt

Sau khi người dùng đồng ý, đã chạy đúng một lần:
`.\.venv\Scripts\python.exe scripts/wda_smoke.py --execute-settings`.
Windows gửi POST tạo session WDA với bundle `com.apple.Preferences`, nhận phản hồi,
chụp ảnh trước và sau bằng WDA. Ảnh sau hiển thị rõ màn hình chính Cài đặt.
Bằng chứng local: `captures/direct-fdbf3c06/{before.png,after.png,result.json}`.
JSON ban đầu verification_uncertain, sau review ảnh được ghi verified_match,
với phương thức review rõ ràng; khác biệt hash riêng lẻ không được coi là xác minh.
Không TTS, không Voice Control, không sửa tùy chọn trong Cài đặt. Ảnh chưa được gửi
qua Deepgram/AI Gateway trong phép thử; chỉ lưu local và kiểm tra ảnh trong phiên làm việc.
Các mục chưa đạt bên dưới là lịch sử khảo sát, được kết quả mới này thay thế.

## CLI direct tối thiểu

Chỉ mở Cài đặt theo bundle ID; chưa hỗ trợ chạm tùy ý, tọa độ hoặc app khác.
Lõi `direct.py` trả ActionResult, interface DirectBackend nhỏ; `wda.py` thực thi.
CLI cũ vẫn giữ nguyên, không có automatic fallback giữa direct và TTS.
`intent.py` nhận thêm system_prompt tùy chọn, mặc định cũ giữ nguyên.
`verification.py` có hàm verify_screen trả dữ liệu, CLI cũ gọi lại hàm này.
Không sửa `session.py` untracked của người dùng.

```powershell
# Preview offline, không chụp/gửi ảnh hoặc gọi AI
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli "mở Cài đặt"
# Thực thi sau xác nhận y, chỉ lưu ảnh local
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli "mở Cài đặt" --execute
# Giọng nói + hiểu ý định + đánh giá ảnh, dùng dịch vụ/model hiện có
.\.venv\Scripts\python.exe -m iphone_assistant.direct_cli --listen --ai --execute --verify
# Tests thông thường không gọi cloud hoặc iPhone
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Một lượt chỉ có tối đa một hành động, không tự retry. Mỗi request WDA có socket
timeout 30 giây, registry 5 giây; API intent 30 giây, vision 60 giây theo code cũ.
Chờ input của người dùng không có timeout. Ctrl+C dừng lượt; nếu POST đã gửi thì
kết quả chưa rõ, không tự gửi lại. Không có chế độ bỏ xác nhận. Enter kết thúc
thu âm, chưa tự nhận biết nói xong. Các trạng thái canceled, needs_clarification,
target_not_found, action_sent, verified_match/mismatch, verification_uncertain,
error và dry_run được trả riêng. action_sent không có nghĩa đã kiểm chứng.
Không giữ mục tiêu hoặc ảnh từ lượt trước. Backend direct không phát âm thanh.

Đã chạy 13 unit tests đạt, compileall và git diff --check đạt; preview CLI và
WDA status đạt. Có test mock cho hủy, mơ hồ, lỗi, timeout không retry, tách trạng
thái và không tái dùng mục tiêu. **Luồng mới microphone → AI → direct → AI verify
chưa chạy end-to-end**, không gửi thêm ảnh hay mở Cài đặt lần nữa trong đợt này.

## Khởi động lại runtime đã thiết lập

Các lệnh này không cần chạy khi WDA đang ready. Nếu mất USB, dừng thao tác và
kiểm tra lại trạng thái; không tự lặp yêu cầu trước. Sau reboot, mở khóa iPhone,
kiểm tra profile còn hạn và kết nối USB. Dùng Python môi trường DDI:

```powershell
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/start_direct.py tunnel
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/ddi_userspace.py
# Chỉ khi DDI chưa có và bạn chủ động đồng ý mount/personalize:
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/ddi_userspace.py --mount
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/start_direct.py wda
.\.venv\Scripts\python.exe scripts/wda_smoke.py
```

Script start_direct từ chối khi PID ios.exe cũ còn sống; không tự kill/restart.
PID/log nằm trong artifacts/direct-setup. Khi cần dừng, kiểm tra PID/path bằng
Get-Process trước khi Stop-Process đúng tiến trình của phiên này. Startup helper
đã compile/help-check; chuỗi khôi phục sau reboot chưa thử vật lý.
Hết hạn profile miễn phí: ký/cài lại cùng gói no-dsym và account trong Sideloadly,
không tự thu hồi certificate. Nếu Trust/UI Automation yêu cầu nhập mật mã,
người dùng tự nhập trên iPhone, không gửi vào chat.
go-ios cũng tạo `selfIdentity.plist` ở thư mục làm việc; không đọc/in nội dung.
Đã thêm Git ignore cho file này, P12 và mobileprovision để tránh commit identity.

Để hoàn tác: dừng đúng hai tiến trình tunnel/WDA đã tạo, gỡ WDA trên iPhone nếu
muốn, gỡ Sideloadly bằng Apps của Windows nếu không cần. Venv/artifact mới nằm
trong artifacts/direct-setup; DDI cache ở thư mục người dùng đã ghi bên dưới.
Không xóa môi trường .venv-device-x64 hoặc pairing record. Việc gỡ DDI đang mount
cần dùng công cụ cryptex phù hợp; không tự xóa thư mục hệ thống trên iPhone.

## Kiểm tra trạng thái hiện tại

Chạy `scripts/wda_smoke.py` không có cờ thực thi để đọc WDA qua userspace tunnel.
Rà soát trước push ngày 18/11/2026: `wda_ready=true`, 13 unit tests đạt,
compileall đạt. Không thực hiện thêm thao tác trên iPhone.
`direct_doctor.py` là phép dò USB ban đầu, luôn trả exit 1 vì không chứng nhận
milestone; cổng USB 8100 đóng không phủ định WDA hoạt động qua tunnel.

## Nhật ký thiết lập (lịch sử)

Các ghi chú dưới đây mô tả từng thời điểm trước khi đạt milestone; các câu
“chưa đạt”, “chưa chạy” và đề xuất xin phép không phải trạng thái hiện tại.
Trạng thái và lệnh sử dụng hiện tại nằm ở các mục phía trên.

<details>
<summary>Xem lịch sử khảo sát, ký gói và thiết lập DDI</summary>

## DDI và WDA đã hoạt động, đang chờ smoke test

Người dùng đã cho phép personalization/mount DDI. Cài pymobiledevice3 11.58.0
trong `artifacts/direct-setup/venv-ddi` (venv riêng, có system-site-packages);
không nâng cấp `.venv-device-x64`. Phiên bản mới kỳ vọng đúng DDI build 27B52.
`scripts/ddi_userspace.py` dùng dialer theo giao thức userspace của go-ios,
không tạo interface hệ thống. `--mount` được chạy một lần; thiết bị trả DDI
`com.apple.MobileAsset.DDI`, version `27.2.52.0`. RSD sau đó có cả
`com.apple.dt.testmanagerd.remote` và `.remote.automation`.
Khởi chạy lại WDA bằng go-ios: XCTest authorized, HTTP `/status` trả 200 và
`ready=true`. Chưa có bằng chứng thao tác UI. Tunnel/WDA còn chạy, PID/log ở
`artifacts/direct-setup/`; không commit log hoặc identifier thiết bị.

```powershell
# Chỉ đọc DDI/RSD, không mount
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/ddi_userspace.py
# Chỉ đọc trạng thái WDA
.\.venv\Scripts\python.exe scripts/wda_smoke.py
# Chỉ chạy sau khi đồng ý thử mở Cài đặt và chụp ảnh local
.\.venv\Scripts\python.exe scripts/wda_smoke.py --execute-settings
```

Smoke test chụp trước, tạo phiên WDA mở `com.apple.Preferences`, chụp sau.
Không TTS/cloud, không tọa độ, không đổi tùy chọn; không tự retry POST.
Ảnh và JSON lưu trong `captures/direct-*/`. API thành công chỉ là action_sent;
script để verification_uncertain cho đến khi ảnh được kiểm tra thực tế.

## Sau khi Trust: tunnel đạt, thiếu dịch vụ XCTest

Người dùng xác nhận Trust đã xong. Đã chạy go-ios 1.3.2
`tunnel start --userspace --tunnel-info-host=127.0.0.1 --tunnel-info-port=28100`
với UDID chỉ định nội bộ: API trả một tunnel userspace, listener 28101.
Không Administrator, driver hoặc firewall mới. PID lưu tại
`artifacts/direct-setup/tunnel.pid`; log trong cùng thư mục bị Git ignore.
Tunnel còn chạy để tiếp tục kiểm tra; có thể dừng đúng PID sau khi xác minh đó
vẫn là tiến trình ios.exe của phiên này.

Thử `runwda` với bundle đã cài, `--xctestconfig=WebDriverAgentRunner.xctest`,
address/RSD/userspace port từ tunnel. Tiến trình đã thoát với lỗi
`com.apple.dt.testmanagerd.remote is not available in RSD`.
`image list` báo none. Chưa gửi thao tác UI hoặc lấy ảnh sau thao tác.

Đọc implementation pymobiledevice3 11.50.3 cho thấy iOS 27 dùng Cryptex DDI,
không nên chạy mù `go-ios image auto` với image cũ. Đã tải **chỉ artifact** bằng
`fetch_cryptex_ddi()` từ repository doronz88/DeveloperDiskImage vào
`C:\Users\quanl\.pymobiledevice3\Xcode_iOS_DDI_Cryptex`.
Manifest thực tế build 27B52, trong khi thư viện kỳ vọng 27A5228h và phát cảnh báo.
Chưa mount/personalize; cần đối chiếu phiên bản công cụ trước khi mount.
Personalization có thể gửi ECID, chip/board ID, nonce và metadata image tới
Apple TSS để lấy chữ ký. Cần người dùng đồng ý việc truyền dữ liệu và mount DDI
trước bước đó; không cần mật khẩu Apple cho TSS.

## Kết quả cài gói không có dSYM

Sideloadly 0.72 báo Done sau lần thử gói no-dsym. Kiểm tra lại bằng doctor
đã thấy bundle WDA có hậu tố Personal Team trong danh sách app trên iPhone.
USB, pairing và Developer Mode vẫn hoạt động. Cổng thiết bị 8100 vẫn trả
ConnectionFailedError: **cài runner đạt, khởi chạy WDA/điều khiển chưa đạt**.
Chưa xác minh Trust developer profile, UI Automation hoặc RemoteXPC.
Đã đọc trợ giúp `ios.exe runwda --help`, chưa gửi lệnh khởi chạy runner.

## Lỗi ký dSYM và gói thử sửa

Ảnh lỗi người dùng cung cấp: Sideloadly 0.72 báo `SignBinary` code -69,
`macho sign/edit failed (-40)` tại
`PlugIns/WebDriverAgentRunner.xctest.dSYM/Contents/Resources/DWARF/WebDriverAgentRunner`.
Đây là lỗi xử lý/ký debug symbols; chưa chứng minh lỗi executable XCTest.
Đã tạo `artifacts/direct-setup/WebDriverAgent-17.0.2-no-dsym-unsigned.ipa`
bằng `scripts/prepare_wda_ipa.py --omit-debug-symbols`.
Chỉ bỏ 9 entries thuộc đúng thư mục dSYM; 18 entries còn lại byte-identical
với IPA gốc, gồm executable host, `.xctest` và framework. CRC đạt, bản gốc giữ nguyên.
SHA-256 IPA mới: `6fddeb1e7780df40021c3ecf86ccc90f0cdaa21e6b773d2fd7215bbf33fe752e`.
Chưa ký/cài thành công gói mới; người dùng cần chọn gói này để thử lại trong
Sideloadly. Không bật Remove PlugIns vì có thể xóa runner thực thi.

## Cập nhật sau khi người dùng cài Sideloadly

Đã kiểm tra tiến trình `sideloadly` với cửa sổ `Sideloadly! v0.72`, chạy từ
`C:\Users\quanl\AppData\Local\Sideloadly\Sideloadly.exe`; daemon cũng đang chạy.
Đây là xác nhận ứng dụng đã cài/mở, chưa xác nhận đăng nhập hoặc ký WDA.
iTunes Microsoft Store vẫn hiện diện; chưa thấy iCloud/Apple Application Support
trong danh sách uninstall đã kiểm tra. Chưa kết luận thiếu dependency chỉ từ registry.
Doctor chạy lại: một iPhone USB, pairing/Developer Mode true, không thấy WDA,
cổng 8100 trả ConnectionFailedError. Kênh đọc giao diện vẫn lỗi native pipe,
nên chưa xác minh Sideloadly nhận thiết bị hoặc có hộp thoại dependency nào.

## Khảo sát ngày 18/11/2026

Repo `C:\personal-ai-assistant-ios`, nhánh `main`, commit nền `49d6764`.
`src/iphone_assistant/session.py` đã untracked trước đợt này và được giữ nguyên.
Không pull, reset, stash, commit, push hay sửa repository từ xa.

| Kiểm tra | Kết quả thực tế |
| --- | --- |
| Python chính / `.venv` | 3.12.10 ARM64 |
| `.venv-device-x64` | Python 3.12.10, binary AMD64 chạy trên Windows ARM64 |
| Công cụ thiết bị có sẵn | pymobiledevice3 11.50.3 |
| Node / npm có sẵn | 24.16.0 / 11.13.0 |
| USB | Một iPhone, driver Apple USB có trạng thái OK |
| Thông tin từ lockdown | ProductType `iPhone19,7`, iOS `27.0`, build `24A437` |
| Pairing / Developer Mode | Đã bật; không tạo pairing mới |
| WDA qua danh sách app | Không thấy tên/bundle chứa webdriver, xctrunner hoặc appium |
| Cổng 8100 trên iPhone qua USB | `ConnectionFailedError` |
| Cổng host 8100 / 4723 | Không có listener tại thời điểm khảo sát |
| Người dùng xác nhận | Chưa có WDA; Apple Account miễn phí; không có Mac |

ProductType là mã thiết bị trả về, chưa ánh xạ độc lập sang tên thương mại.
Phép dò tên app không loại trừ một runner có tên tùy chỉnh; cổng mặc định đóng
không loại trừ WDA trên cổng khác. Tuy nhiên người dùng đã xác nhận chưa có WDA.

**Chưa gửi thao tác trực tiếp, chưa lấy screenshot sau thao tác, chưa chứng minh
milestone.** Không gọi TTS, không gửi dữ liệu lên cloud trong đợt khảo sát.
Chưa kiểm chứng UI Automation, DDI, tunnel RemoteXPC hoặc quyền XCTest.

## Chạy lại kiểm tra ngay

Từ PowerShell tại thư mục repo:

```powershell
.\.venv-device-x64\Scripts\python.exe scripts/direct_doctor.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
```

Doctor chỉ đọc USB/lockdown/danh sách tên runner và thử mở cổng 8100. Không
pair/install/launch, không in UDID, pairing record, danh sách app cá nhân hoặc
nội dung lỗi thô. Timeout tổng mặc định 25 giây, không tự thử lại.
Exit code 1 là có chủ đích: preflight không chứng nhận milestone vật lý.
Test thường dùng mock, không kết nối iPhone. Bốn test đã đạt; compileall đạt.

## Đường kỹ thuật được tài liệu hỗ trợ

[Non-macOS Hosts](https://appium.github.io/appium-xcuitest-driver/latest/guides/non-macos-hosts/)
cho phép thiết bị thật iOS 18+ trên Windows với RemoteXPC, UDID và platformVersion
chỉ định rõ. Cần WDA preinstalled hoặc WDA đang chạy do bên ngoài quản lý.
Windows không chạy đường build WDA bằng Xcode.

[Capabilities](https://appium.github.io/appium-xcuitest-driver/latest/reference/capabilities/):
`webDriverAgentUrl` nối WDA đang chạy; `usePreinstalledWDA` chọn runner đã cài;
`prebuiltWDAPath` cung cấp bundle để cài. `usePrebuiltWDA` riêng lẻ vẫn là đường
`xcodebuild test-without-building`, không thay thế `usePreinstalledWDA` trên Windows.

[Preinstalled WDA](https://appium.github.io/appium-xcuitest-driver/latest/guides/run-preinstalled-wda/):
iOS 27 cần RemoteXPC cho cách khởi chạy này; fallback devicectl bị tắt.
Runner cần ký hợp lệ, provisioning được tin cậy và DDI phù hợp; không nhúng
Frameworks/XC** cho đường preinstalled iOS 17+. Không sửa bundle sau ký tùy tiện.

[Prebuilt WDA](https://appium.github.io/appium-xcuitest-driver/latest/guides/run-prebuilt-wda/):
nguồn chính thức từ WDA 16.16.0 là releases của `appium/appium-ios`, tag
`appium-webdriveragent@<version>`. Chọn đúng binary **real device**, đúng phiên bản
dependency; tải binary không cung cấp provisioning cho iPhone của người dùng.

Metadata npm đã đọc bằng `npm.cmd view` (chưa cài): Appium 4.0.0,
XCUITest driver 13.1.1; driver ghim WDA 17.0.2 và appium-ios-remotexpc 6.0.4.
Node/npm hiện có đáp ứng engines công bố. Đây là bộ ứng viên, chưa chứng minh
cài/chạy trên Windows ARM64 này. [Ma trận tương thích](https://appium.github.io/appium-xcuitest-driver/latest/getting-started/system-requirements/)
công bố hỗ trợ iOS 27 từ driver 11.1.2 / WDA 14.1.1 trở lên.

## Blocker ký/provisioning

[Apple Personal Team](https://developer.apple.com/help/account/basics/about-your-developer-account)
được quản lý trong Xcode; provisioning miễn phí hết hạn sau 7 ngày và cần dựng/cài
lại. Tài liệu này không cung cấp workflow ký XCTest runner bằng tài khoản miễn phí
hoàn toàn trên Windows. Chưa xác minh giải pháp sideload nào đáp ứng WDA/iOS 27
trên máy này. Không kết luận rằng mọi giải pháp Windows đều bất khả thi, nhưng
chưa có đường đủ bằng chứng để tiến hành đăng nhập hoặc cài runner.

Bước tiếp theo cần giải quyết là nguồn runner ký hợp lệ cho thiết bị và quyền
XCTest, không phải tích hợp AI. Không cần mua Developer Program chỉ để thử vận may:
tài khoản trả phí riêng lẻ cũng chưa chứng minh đường ký/chạy.
Nếu sau này có quyền dùng máy macOS để chuẩn bị runner, cần thống nhất rõ trước;
hiện chưa sử dụng máy/dịch vụ bên ngoài. Không gửi mật khẩu, 2FA hoặc private key
vào chat. Việc dùng certificate/provisioning và cài runner phải được người dùng
cho phép theo mục 6 của yêu cầu.

## Thiết lập và milestone còn phải thực hiện

1. Có runner đã ký/provisioning cho thiết bị, kiểm tra bundle ID và hạn profile.
2. Xin phép trước khi cài runner, thay driver/service, bật Trust/Developer Mode
   hoặc chạy Administrator. Các trạng thái đã bật không cần bật lại.
3. Thiết lập DDI/RemoteXPC theo [hướng dẫn tunnel](https://appium.github.io/appium-xcuitest-driver/latest/guides/remotexpc-tunnels-real-devices/).
   Đường dự kiến là PC → Apple USB/usbmux → RemoteXPC/CoreDevice → WDA.
   Tunnel tạo interface mạng có thể cần quyền cao; chưa chạy hoặc mở firewall.
   Chỉ bind dịch vụ điều khiển vào loopback khi cấu hình.
4. Chạy WDA, kiểm tra HTTP status; API trả lời chưa chứng minh thao tác.
5. Thống nhất thử mở Cài đặt, chụp trước, gửi đúng một lệnh trực tiếp, chụp sau
   và kiểm tra app/màn hình thực tế. Không đổi tùy chọn trong Cài đặt.
6. Chỉ khi đạt bước 5 mới thêm backend direct và test hành vi vào luồng AI.

Chưa có lệnh chạy backend direct trong ứng dụng. Không dùng `--speak` để thay thế.
Nếu kết nối mất hoặc timeout sau gửi lệnh, dừng và quan sát lại; không phát lại
tự động. Sau reboot cần mở khóa, kiểm tra kết nối/DDI, khởi động lại tunnel
và runner rồi kiểm tra status; sau hết hạn provisioning cần ký/cài lại với phép
của người dùng. Các bước khôi phục này chưa thử trên cấu hình hiện tại.

## Luồng cũ và hoàn tác

Các dependency ứng dụng nếu thiết lập môi trường mới:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[windows,speech,intent]"
```

Không chạy lại lệnh cài trong đợt này vì môi trường đã có. Chụp ảnh dùng môi trường
thiết bị riêng; chưa nâng cấp hoặc sửa môi trường này.

```powershell
# Preview cũ: vẫn chụp/gửi ảnh qua AI Gateway sau xác nhận
.\.venv\Scripts\python.exe -m iphone_assistant.numbered_vision "Tìm Cài đặt"
# TTS cũ: cần giọng trong cấu hình và xác nhận; không phải direct
.\.venv\Scripts\python.exe -m iphone_assistant.numbered_vision --speak --verify --expect "Cài đặt đang mở" "Tìm Cài đặt"
```

Luồng nghe dùng Enter kết thúc thu âm, chưa có endpoint detection.
Không thay Deepgram, AI Gateway hoặc model. `session.py` cũ dùng `/quit` để thoát.

Đợt khảo sát đầu không cài dependency, driver, service hoặc runner mới. Công cụ
portable chuẩn bị ở đợt tiếp theo được liệt kê bên dưới. Muốn bỏ thay đổi khảo sát: xóa riêng `scripts/direct_doctor.py`,
`tests/test_direct_doctor.py`, tài liệu này và hoàn tác đoạn Status trong README
bằng review diff. Không xóa `.venv*`, dữ liệu người dùng hoặc `session.py`.

## Khảo sát tiếp: phương án thử Windows / tài khoản miễn phí

Đã đọc [hướng dẫn SideTap](https://github.com/ucsandman/SideTap/blob/main/docs/setup-windows.md)
và [mã signing](https://github.com/ucsandman/SideTap/blob/main/src/phone_harness/signing.py).
Tác giả mô tả Sideloadly tạo profile miễn phí, rồi go-ios ký lại bundle XCTest
bằng identity/profile của chính người dùng. Workflow được ghi nhận với Sideloadly
0.60; tài liệu cảnh báo lỗi ký với 0.72 và không bảo đảm mọi phiên bản WDA.
Đây là bằng chứng về một đường thử, **không phải xác nhận cho iOS 27 trên máy này**.
Không cài SideTap hoặc chạy script tự động của nó; code có bước đọc identity,
ký, cài và tự khởi chạy nên không phù hợp để chạy trước khi được phép.

[Sideloadly](https://sideloadly.io/) công bố Windows, tài khoản miễn phí và iOS 27+,
nhưng không chứng nhận riêng tổ hợp WDA 17.0.2 / XCTest / Windows ARM64.
Trang tải hiển thị 0.71.0, khác phiên bản 0.72 được báo trong SideTap; cần lấy
phiên bản thực tế từ công cụ khi chạy, không suy đoán từ tên file.
Trang yêu cầu iTunes/iCloud bản web; chưa cài/gỡ các phần mềm này.
[Chính sách dữ liệu](https://sideloadly.io/privacy) nói tài khoản/mật khẩu gửi đến
Apple; tùy chọn Remote Anisette dùng server của họ và lộ IP, OS, phiên bản công cụ.
Chưa cho phép hoặc sử dụng Remote Anisette. Không yêu cầu nhập thông tin Apple vào chat.

Đã chuẩn bị local trong `artifacts/direct-setup/` (được Git ignore):

| Artifact | Nguồn / xác minh |
| --- | --- |
| `WDA-17.0.2.zip` | [Appium release](https://github.com/appium/appium-ios/releases/tag/appium-webdriveragent%4017.0.2), real-device build |
| `WebDriverAgent-17.0.2-unsigned.ipa` | Đóng lại dưới `Payload/`, giữ đủ 27 entries và `.xctest`; kiểm tra CRC đạt |
| `go-ios-v1.3.2-win.zip`, `ios.exe` | [go-ios release](https://github.com/danielpaulus/go-ios/releases/tag/v1.3.2), portable trong repo |
| `wda-package-manifest.json` | SHA-256, bundle ID, trạng thái chưa ký/chưa cài |
| `SideloadlySetup64.exe` | Tải từ `https://sideloadly.io/SideloadlySetup64.exe`; 144153593 bytes; chưa chạy |

Bộ cài Sideloadly trả `NotSigned` khi kiểm tra Authenticode, không có
ProductVersion/FileVersion trong metadata PE. SHA-256 local (không có checksum
độc lập của tác giả để đối chiếu):
`2e7d9a80bcd7912a9a2dae1969645f8af386af46802a79303e727773b506362e`.
Cần nêu rõ điều này khi xin phép chạy bộ cài; không đổi execution policy hoặc
bỏ qua cảnh báo hệ thống. Phiên bản thực tế vẫn chưa xác minh.

Sau khi người dùng cho phép chạy bộ cài: đã đối chiếu lại SHA-256 và mở
`SideloadlySetup64.exe`. Tiến trình hiện cửa sổ `Sideloadly! v0.72 Setup`,
xác nhận phiên bản trình cài là 0.72 (khác trang tải ghi 0.71.0).
Chưa xác nhận cài đặt hoàn tất. Kênh Computer Use báo native pipe unavailable
sau thử lại/reset, nên chưa đọc/bấm được trình cài. Không tự chạy silent install,
không đăng nhập Apple, không cài WDA hoặc thêm dependency hệ thống.

SHA-256 ZIP WDA đối chiếu digest GitHub:
`4209939f45d66b1fbd8e036effcc13637cddceaa12e3db8636c47ca645e2ebc5`.
SHA-256 ZIP go-ios đối chiếu digest GitHub:
`939c6bcaafed183a92afb9f79cc11b1f935fa6389bfc94d3902e3f52c4dff3fe`.
IPA tạo local:
`ffbda38a746739f9eb0f310f08fead36ae8d32cef7ecbc387a7f388d9ac70868`.
Hash xác nhận file nhận được khớp nguồn phát hành; không chứng nhận khả năng chạy.

Đã chạy `ios.exe --version` → 1.3.2, `sign app --help`, `tunnel start --help`.
Binary chạy được trên host này. Chưa chạy sign, install, tunnel hoặc wda.
`sign app` nhận P12/profile có sẵn; không tự cấp profile Apple miễn phí.
`tunnel start` có thể pair, nên cũng chưa chạy trước khi được phép.

```powershell
# Chỉ xem trợ giúp, không ký/cài
.\artifacts\direct-setup\ios.exe sign app --help
# Đóng IPA nếu chưa tồn tại; script từ chối ghi đè
.\.venv\Scripts\python.exe scripts/prepare_wda_ipa.py
```

Đề xuất bước được duyệt tiếp theo: cài/mở Sideloadly, kiểm tra dependency thực tế,
sau đó người dùng đăng nhập trực tiếp để thử ký/cài IPA đã chuẩn bị. Xin phép riêng
nếu cần thêm iTunes/iCloud/driver hoặc Remote Anisette. Không tự gỡ driver đang hoạt động.
Nếu ký cài thành công nhưng XCTest lỗi, kiểm tra chữ ký nested bundle trước khi
dùng identity/profile để ký lại; thao tác đó cũng cần phép của người dùng.
Không bật tự refresh, không lưu passcode iPhone, không đổi nhà cung cấp AI.

Hoàn tác phần chuẩn bị: xóa riêng thư mục `artifacts/direct-setup/` sau khi đóng
công cụ và xóa script `scripts/prepare_wda_ipa.py` nếu không dùng. Không có thay đổi PATH,
service, firewall hoặc môi trường Python từ phần chuẩn bị này.

</details>
