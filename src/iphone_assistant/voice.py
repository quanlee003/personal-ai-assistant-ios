from pathlib import Path

import argparse
import os
from dotenv import load_dotenv

from .intent import IntentError, understand_intent
from .speech import (
    SpeechInputError,
    record_wav,
    transcribe_vietnamese,
)
from .tts import SpeechError, WindowsSpeaker
from .voice_control import (
    UnsupportedVoiceControlCommand,
    build_instruction,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    load_dotenv(
        dotenv_path=project_root / ".env",
        override=False,
    )

    parser = argparse.ArgumentParser(
        description=(
            "Thu tiếng Việt qua microphone, nhận dạng "
            "bằng Deepgram và tạo lệnh Voice Control."
        )
    )

    parser.add_argument(
        "--speak",
        action="store_true",
        help="Cho phép phát lệnh sau khi bạn xác nhận",
    )

    parser.add_argument(
        "--voice-id",
        default=os.environ.get("TTS_VOICE_ID", "").strip(),
        help=(
            "ID giọng TTS tiếng Anh; "
            "mặc định đọc TTS_VOICE_ID từ .env"
        ),
    )

    parser.add_argument(
        "--mic-device",
        type=int,
        default=None,
        help="ID microphone; mặc định dùng thiết bị hệ thống",
    )

    parser.add_argument(
        "--rate",
        type=int,
        default=150,
        help="Tốc độ TTS, từ 80 đến 250",
    )

    args = parser.parse_args()

    if not os.environ.get("DEEPGRAM_API_KEY", "").strip():
        parser.error(
            "Chưa đặt biến môi trường DEEPGRAM_API_KEY."
        )

    if args.speak and not args.voice_id:
        parser.error(
            "Chưa có giọng TTS. "
            "Đặt TTS_VOICE_ID trong .env "
            "hoặc truyền --voice-id."
        )

    if not 80 <= args.rate <= 250:
        parser.error("--rate phải nằm trong khoảng 80–250.")

    speaker = None

    try:
        if args.speak:
            speaker = WindowsSpeaker()

            available_ids = {
                voice.id
                for voice in speaker.list_voices()
            }

            if args.voice_id not in available_ids:
                raise SpeechError(
                    "Voice ID không tồn tại. "
                    "Dùng CLI --list-voices để xem lại."
                )

        print(
            "Lượt thu này sẽ được gửi đến Deepgram "
            "để nhận dạng tiếng Việt."
        )

        audio = record_wav(device=args.mic_device)

        print("Đang nhận dạng bằng Deepgram...")
        transcript = transcribe_vietnamese(audio)

        print(f"Nhận dạng: {transcript}")

        print("Đang hiểu yêu cầu qua Vercel AI Gateway...")

        result = understand_intent(transcript)

        if result.decision == "clarify":
            print(f"Cần làm rõ: {result.message}")
            print(
                "Chưa thực hiện thao tác. "
                "Chạy lại và nói đầy đủ yêu cầu."
            )
            return

        if result.decision == "unsupported":
            print(f"Chưa hỗ trợ: {result.message}")
            return

        command = result.command

        if command is None:
            raise IntentError(
                "Không có hành động hợp lệ để thực hiện."
            )

        if command.action == "stop":
            print(
                "Đã dừng lượt hiện tại. "
                "Không phát câu lệnh cho iPhone."
            )
            return

        instruction = build_instruction(command)

        print(f"Hành động: {command.action}")
        print(f"Câu Voice Control: {instruction.phrase}")

        if not args.speak:
            print(
                "Chế độ xem trước: không phát âm thanh. "
                "Thêm --speak và --voice-id để phát."
            )
            return

        confirmation = input(
            "Nhập y rồi Enter để phát lệnh; "
            "Enter để hủy: "
        )

        if confirmation.strip().casefold() != "y":
            print("Đã hủy. Không phát lệnh.")
            return

        speaker.speak(
            instruction.phrase,
            voice_id=args.voice_id,
            rate=args.rate,
        )

        print(
            "TTS đã hoàn tất phát câu lệnh. "
            "Chưa xác nhận thao tác trên iPhone."
        )

    except (
        SpeechInputError,
        IntentError,
        UnsupportedVoiceControlCommand,
        SpeechError,
    ) as exc:
        parser.exit(1, f"Lỗi: {exc}\n")

    except (KeyboardInterrupt, EOFError):
        print(
            "\nĐã hủy phía máy tính. "
            "Nếu âm thanh đã được phát trước đó, "
            "iPhone vẫn có thể đã nhận lệnh."
        )
        raise SystemExit(130)

    finally:
        if speaker is not None:
            speaker.close()


if __name__ == "__main__":
    main()