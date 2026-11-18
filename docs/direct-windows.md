# Thiết lập và vận hành WDA trên Windows

Hướng dẫn này mô tả cấu hình đã dùng trên máy hiện tại. Chưa có installer tự động
cho máy mới; clone repository không mang theo công cụ, virtualenv, key hoặc runner đã ký.
Cách sử dụng hằng ngày ở [README](../README.md).

## Cấu hình đã kiểm chứng

| Thành phần | Cấu hình local |
| --- | --- |
| Host | Windows 11 ARM64; Python ứng dụng 3.12.10 ARM64 |
| iPhone | Thiết bị trả iOS 27.0, build 24A437; USB, pairing và Developer Mode đã có |
| Runner | Appium WebDriverAgent 17.0.2 real-device build |
| Ký/cài | Sideloadly 0.72, Apple Account miễn phí của người dùng |
| Tunnel | go-ios 1.3.2 userspace, registry `127.0.0.1:28100`, relay 28101 |
| DDI | pymobiledevice3 11.58.0 trong `artifacts/direct-setup/venv-ddi`, build 27B52 |
| Vận hành | Không mở firewall, không tạo interface mạng hệ thống trong đường userspace đã thử |

Đây là kết quả trên cấu hình cụ thể, không phải ma trận tương thích mọi máy/iOS.

## Bốn script được giữ lại

| Script | Khi dùng |
| --- | --- |
| `prepare_wda_ipa.py` | Đóng IPA từ ZIP WDA đã đối chiếu checksum để ký/cài hoặc chuẩn bị lại. |
| `start_direct.py` | Khởi động tunnel/runner đã thiết lập; không ký/cài/pair/mount. |
| `ddi_userspace.py` | Kiểm tra DDI; chỉ mount/personalize khi chủ động thêm `--mount`. |
| `wda_smoke.py` | Chỉ đọc readiness WDA qua tunnel; không có nhánh thực thi UI. |

## Chuẩn bị WDA lần đầu

Nguồn: [Appium build 17.0.2](https://github.com/appium/appium-ios/releases/tag/appium-webdriveragent%4017.0.2),
[go-ios 1.3.2](https://github.com/danielpaulus/go-ios/releases/tag/v1.3.2),
[Sideloadly](https://sideloadly.io/). Tool local nằm trong `artifacts/direct-setup/`.

| File | SHA-256 đã đối chiếu/ghi nhận |
| --- | --- |
| WDA-17.0.2.zip | `4209939f45d66b1fbd8e036effcc13637cddceaa12e3db8636c47ca645e2ebc5` |
| go-ios-v1.3.2-win.zip | `939c6bcaafed183a92afb9f79cc11b1f935fa6389bfc94d3902e3f52c4dff3fe` |
| IPA no-dsym local | `6fddeb1e7780df40021c3ecf86ccc90f0cdaa21e6b773d2fd7215bbf33fe752e` |

Gói WDA có `.xctest.dSYM` khiến Sideloadly báo lỗi ký. Script chỉ bỏ đúng thư mục
debug symbols khi dùng cờ dưới đây, giữ host, `.xctest` và framework. Không bật
Remove PlugIns vì có thể xóa runner thực thi. Script không ghi đè output có sẵn.

```powershell
.\.venv\Scripts\python.exe scripts/prepare_wda_ipa.py --omit-debug-symbols
```

Sau đó ký/cài IPA bằng Sideloadly và tài khoản của chính người dùng. Nhập thông
tin đăng nhập trực tiếp trong công cụ; không ghi password/private key vào repo.
Trên iPhone cần pairing/Trust, Developer Mode và quyền UI Automation phù hợp.
Công cụ không tự bật quyền này. Khi profile hết hạn, cần ký/cài lại và kiểm tra
Trust; chưa có gia hạn tự động. Lịch sử điều tra chi tiết nằm trong Git.

## Runtime

Trước hết kiểm tra trạng thái; đã ready thì không khởi động thêm:

```powershell
.\.venv\Scripts\python.exe scripts/wda_smoke.py
```

Nếu chưa có runtime, kết nối đúng một iPhone USB, mở khóa, rồi chạy từng bước:

```powershell
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/start_direct.py tunnel
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/ddi_userspace.py
```

DDI cần hiện `com.apple.MobileAsset.DDI`, cùng dịch vụ XCTest remote. Nếu thiếu,
lệnh sau có thể gửi ECID/chip/board/nonce và metadata image tới Apple TSS để lấy
chữ ký và mount DDI; chỉ chạy khi đã đồng ý thao tác này:

```powershell
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/ddi_userspace.py --mount
```

Khi DDI sẵn sàng:

```powershell
.\artifacts\direct-setup\venv-ddi\Scripts\python.exe scripts/start_direct.py wda
.\.venv\Scripts\python.exe scripts/wda_smoke.py
```

Startup helper chỉ báo PID đã tạo. `wda_ready=true` mới xác nhận WDA trả lời;
vẫn chưa chứng minh một thao tác thành công. Helper từ chối tạo chồng tiến trình
ios.exe đã ghi nhận; không tự kill PID. PID/log ở `artifacts/direct-setup/`.
Kiểm tra PID và executable trước khi dừng tiến trình bằng Windows. Rút USB hoặc
timeout sau thao tác: dừng, kiểm tra màn hình/bằng chứng trước khi gửi yêu cầu mới.
Khôi phục sau reboot đầy đủ chưa kiểm thử trên thiết bị.

DDI cache hiện có ở thư mục người dùng `.pymobiledevice3/Xcode_iOS_DDI_Cryptex`.
Môi trường `.venv-device-x64` từ khảo sát cũ không còn được ứng dụng import/gọi;
giữ nguyên môi trường local để không can thiệp công cụ thiết bị đã thiết lập.

## Milestone thực tế

Ngày 18/11/2026 đã kiểm chứng:

- Mở Cài đặt trực tiếp, chụp ảnh trước/sau; không phát TTS.
- Tìm `com.apple.settings.battery` là button visible/enabled, kiểm tra lại,
  chạm một lần và thấy trang Pin. Không đổi tùy chọn.
- Hai lượt auto Pin đều `verified_match`, attempted/acknowledged hai bước,
  `error_code=null`. Chưa xác nhận cùng một phiên vì bản ghi chưa có session ID.

Bằng chứng local gồm `captures/battery-smoke-56b1b0d2/`, `captures/direct-0655f042/`
và `captures/direct-5d572462/`; không đưa ảnh/XML lên Git. Không suy ra độ ổn định
trong tiếng ồn hoặc hỗ trợ app khác từ các phép thử này.

API tham khảo: [tìm phần tử WDA](https://github.com/appium/WebDriverAgent/blob/master/WebDriverAgentLib/Commands/FBFindElementCommands.m),
[thuộc tính/click WDA](https://github.com/appium/WebDriverAgent/blob/master/WebDriverAgentLib/Commands/FBElementCommands.m).
Đã thử endpoint trên runner đang cài, không chỉ suy luận từ nhánh master.

## Dọn hoặc hoàn tác setup

Dừng đúng tiến trình tunnel/WDA sau khi đối chiếu PID/path. Có thể gỡ runner
trên iPhone hoặc Sideloadly qua Apps của Windows khi không còn dùng. Không xóa
pairing, identity hoặc môi trường công cụ đang sử dụng. go-ios có thể tạo
`selfIdentity.plist` ở thư mục repo; file này, P12/mobileprovision, `.env`,
`artifacts/`, `captures/` và `runtime/` đều được Git ignore.

Thay đổi source không yêu cầu cài lại/ký lại runner. Test thường dùng mock;
thử thao tác thật qua CLI direct sau khi chủ động cho phép, không dùng script
smoke để mở app nữa.
