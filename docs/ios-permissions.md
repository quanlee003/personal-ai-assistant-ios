# Quyền và thiết lập khi kết nối iPhone

App Windows hiện tại dùng USB để đọc danh mục ứng dụng, WDA để điều hướng.
Không có một quyền “full access” gom tất cả chức năng. Quét app không đọc dữ
liệu bên trong app, không cần HealthKit hoặc bật báo cáo Thời gian sử dụng.

| Điều kiện | Cách kiểm chứng trong bản này | Hành động người dùng |
| --- | --- | --- |
| USB, mở khóa, Tin cậy PC | Phát hiện đúng một máy và đọc installation proxy thành công; lỗi không được coi là đã cấp quyền | Kết nối cáp, mở khóa, chấp nhận Tin cậy khi iOS hỏi |
| WDA và phiên kiểm thử | `/status` trả ready; không suy ra từng trạng thái Developer Mode/provisioning riêng | Thiết lập WDA đã ký, Developer Mode và kết nối kiểm thử |
| Hoạt động ứng dụng & web | Không dò khi quét app; ghi chưa kiểm tra | Nút trong app mở trang Thời gian sử dụng; người dùng tự bật nếu muốn |
| HealthKit | Không áp dụng cho quét app | Chưa có app iOS yêu cầu quyền này |
| Family Controls | Chưa tích hợp | Cần app iOS, capability/entitlement và luồng cấp quyền riêng |

Nút mở Thời gian sử dụng kiểm tra WDA thuộc đúng máy vừa quét, điều hướng có
giới hạn, kiểm tra trang đích và không bấm nút Bật/Allow. Khi timeout hoặc trang
khác dự kiến, hiển thị đường dẫn thủ công; không gửi lại thao tác chưa rõ kết quả.
Đây là điều hướng UI bằng WDA, không phải deep link công khai hay hộp thoại API
cấp quyền Screen Time cho app Windows. Mở trang thành công không có nghĩa đã bật.

## Kết quả nghiên cứu API Apple

- [HealthKit authorization](https://developer.apple.com/documentation/healthkit/authorizing-access-to-health-data):
  app iOS phải có HealthKit capability và xin quyền theo loại dữ liệu. Quyền
  Sức khỏe không cấp quyền điều khiển ứng dụng khác.
- [Family Controls](https://developer.apple.com/documentation/familycontrols):
  cần capability trước khi dùng AuthorizationCenter. Đây là chức năng riêng,
  không đồng nghĩa đọc được toàn bộ dữ liệu Screen Time bằng app Windows.
- [requestAuthorization(for:)](https://developer.apple.com/documentation/familycontrols/authorizationcenter/requestauthorization(for:)):
  yêu cầu cấp quyền cho cá nhân hoặc trẻ em, có bước xác thực do hệ thống quản lý.
- [openSettingsURLString](https://developer.apple.com/documentation/uikit/uiapplication/opensettingsurlstring):
  API công khai mở trang cài đặt của chính app, không phải API mở tùy ý mọi trang
  hệ thống. Bản hiện tại không dựa vào URL `App-prefs:` không được bảo đảm.

Các API native trên là hướng phát triển app đồng hành iOS, chưa được triển khai
trong bản Windows này. Danh mục app và hồ sơ thiết bị luôn ở local; chưa gửi AI.
