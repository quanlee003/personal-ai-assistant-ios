import re
from dataclasses import dataclass

from .commands import Command


class UnsupportedVoiceControlCommand(ValueError):
    pass


@dataclass(frozen=True)
class VoiceControlInstruction:
    phrase: str


SWIPE_PHRASES = {
    "right": "Swipe right",
    "left": "Swipe left",
    "up": "Swipe up",
    "down": "Swipe down",
}

FIXED_PHRASES = {
    "go_home": "Go home",
    "show_numbers": "Show numbers",
    "show_names": "Show names",
}

# Tên người dùng/model trả về -> tên phát cho Voice Control.
# Chỉ thêm app khi bạn muốn hỗ trợ nó.
APP_NAMES = {
    "youtube": "YouTube",
    "safari": "Safari",
    "settings": "Settings",
    "cài đặt": "Settings",
    "chrome": "Chrome",
    "google chrome": "Chrome",
    "spotify": "Spotify",
}


def build_instruction(
    command: Command,
) -> VoiceControlInstruction:
    if command.action == "swipe":
        direction = command.arguments.get("direction")
        phrase = SWIPE_PHRASES.get(direction)

        if phrase is None:
            raise UnsupportedVoiceControlCommand(
                f"Hướng vuốt không hợp lệ: {direction!r}"
            )

        return VoiceControlInstruction(phrase=phrase)

    if command.action in FIXED_PHRASES:
        if command.arguments:
            raise UnsupportedVoiceControlCommand(
                "Hành động này không nhận tham số."
            )

        return VoiceControlInstruction(
            phrase=FIXED_PHRASES[command.action]
        )

    if command.action == "open_app":
        app_name = command.arguments.get("app_name", "")
        normalized = " ".join(app_name.casefold().split())
        spoken_name = APP_NAMES.get(normalized)

        if spoken_name is None:
            raise UnsupportedVoiceControlCommand(
                f"Chưa cấu hình tên app: {app_name!r}. "
                "Thêm tên vào APP_NAMES trước khi sử dụng."
            )

        return VoiceControlInstruction(
            phrase=f"Open {spoken_name}"
        )

    if command.action == "select_target":
        target = command.arguments.get("target", "").strip()

        if not re.fullmatch(r"[1-9][0-9]{0,2}", target):
            raise UnsupportedVoiceControlCommand(
                "Hiện chỉ chọn phần tử theo số từ 1–999. "
                "Hãy yêu cầu hiện số rồi chọn số đang thấy. "
                "Chưa tự đoán nhãn nút hoặc vị trí."
            )

        return VoiceControlInstruction(
            phrase=f"Tap {int(target)}"
        )

    if command.action == "stop":
        raise UnsupportedVoiceControlCommand(
            "Stop là tín hiệu dừng nội bộ, "
            "không chuyển thành câu lệnh cho iPhone."
        )

    raise UnsupportedVoiceControlCommand(
        f"Chưa có bộ thực thi cho {command.action!r}. "
        "Không có âm thanh nào được phát."
    )