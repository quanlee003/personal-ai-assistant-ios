import argparse
import json

from .commands import UnsupportedCommand, parse_command
from .tts import SpeechError, WindowsSpeaker
from .voice_control import (
    UnsupportedVoiceControlCommand,
    build_instruction,
)


def print_json(data: dict) -> None:
    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Phân tích lệnh tiếng Việt và phát "
            "câu Voice Control trên Windows."
        )
    )

    parser.add_argument(
        "text",
        nargs="?",
        help="Một câu lệnh, đặt trong dấu nháy",
    )

    mode = parser.add_mutually_exclusive_group()

    mode.add_argument(
        "--preview",
        action="store_true",
        help="Xem câu Voice Control, không phát âm thanh",
    )

    mode.add_argument(
        "--speak",
        action="store_true",
        help="Phát câu Voice Control qua Windows",
    )

    mode.add_argument(
        "--list-voices",
        action="store_true",
        help="Liệt kê các giọng TTS trên Windows",
    )

    parser.add_argument(
        "--voice-id",
        help="ID của giọng tiếng Anh dùng để phát lệnh",
    )

    parser.add_argument(
        "--rate",
        type=int,
        default=150,
        help="Tốc độ đọc, mặc định 150",
    )

    args = parser.parse_args()

    if args.list_voices:
        if args.text:
            parser.error(
                "--list-voices không nhận câu lệnh."
            )

        speaker = None

        try:
            speaker = WindowsSpeaker()

            print_json(
                {
                    "voices": [
                        {
                            "id": voice.id,
                            "name": voice.name,
                        }
                        for voice in speaker.list_voices()
                    ]
                }
            )
        except SpeechError as exc:
            parser.error(str(exc))
        finally:
            if speaker is not None:
                speaker.close()

        return

    if not args.text:
        parser.error("Cần nhập một câu lệnh.")

    try:
        command = parse_command(args.text)
    except UnsupportedCommand as exc:
        parser.error(str(exc))

    if command.action == "stop":
        print_json(
            {
                "status": "no_active_task",
                "audio_emitted": False,
                "device_action_verified": False,
                "command": command.to_dict(),
                "message": (
                    "CLI hiện chạy từng lệnh độc lập; "
                    "chưa có tác vụ nền để hủy."
                ),
            }
        )
        return

    if not args.preview and not args.speak:
        print_json(
            {
                "status": "parsed_only",
                "executed": False,
                "command": command.to_dict(),
            }
        )
        return

    try:
        instruction = build_instruction(command)
    except UnsupportedVoiceControlCommand as exc:
        parser.error(str(exc))

    if args.preview:
        print_json(
            {
                "status": "preview",
                "audio_emitted": False,
                "device_action_verified": False,
                "command": command.to_dict(),
                "voice_control_phrase": instruction.phrase,
            }
        )
        return

    if not args.voice_id:
        parser.error(
            "--speak cần --voice-id. "
            "Dùng --list-voices để chọn giọng tiếng Anh."
        )

    speaker = None

    try:
        speaker = WindowsSpeaker()

        speaker.speak(
            instruction.phrase,
            voice_id=args.voice_id,
            rate=args.rate,
        )
    except SpeechError as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        print_json(
            {
                "status": "interrupted",
                "device_action_verified": False,
                "message": (
                    "Đã ngắt phía máy tính. "
                    "Lệnh có thể đã được iPhone nghe trước đó."
                ),
            }
        )
        raise SystemExit(130)
    finally:
        if speaker is not None:
            speaker.close()

    print_json(
        {
            "status": "audio_emitted",
            "audio_emitted": True,
            "device_action_verified": False,
            "command": command.to_dict(),
            "voice_control_phrase": instruction.phrase,
        }
    )


if __name__ == "__main__":
    main()