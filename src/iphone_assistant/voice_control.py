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

    if command.action == "stop":
        raise UnsupportedVoiceControlCommand(
            "Stop là tín hiệu dừng nội bộ, "
            "không chuyển thành câu lệnh cho iPhone."
        )

    raise UnsupportedVoiceControlCommand(
        f"Chưa có bộ thực thi cho {command.action!r}. "
        "Không có âm thanh nào được phát."
    )