import sys
from dataclasses import dataclass


class SpeechError(RuntimeError):
    pass


@dataclass(frozen=True)
class InstalledVoice:
    id: str
    name: str


class WindowsSpeaker:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise SpeechError(
                "Bộ phát này chỉ hỗ trợ Windows."
            )

        try:
            import pyttsx3
        except ImportError as exc:
            raise SpeechError(
                "Thiếu dependency TTS. "
                'Chạy: python -m pip install -e ".[windows]"'
            ) from exc

        try:
            self._engine = pyttsx3.init("sapi5")
        except Exception as exc:
            raise SpeechError(
                f"Không khởi tạo được SAPI5: {exc}"
            ) from exc

    def list_voices(self) -> list[InstalledVoice]:
        try:
            voices = self._engine.getProperty("voices")

            return [
                InstalledVoice(
                    id=voice.id,
                    name=voice.name or voice.id,
                )
                for voice in voices
            ]
        except Exception as exc:
            raise SpeechError(
                f"Không đọc được danh sách giọng: {exc}"
            ) from exc

    def speak(
        self,
        text: str,
        *,
        voice_id: str,
        rate: int = 150,
    ) -> None:
        if not text.strip():
            raise SpeechError("Nội dung phát âm thanh trống.")

        if not 80 <= rate <= 250:
            raise SpeechError(
                "Tốc độ đọc phải nằm trong khoảng 80–250."
            )

        available_ids = {
            voice.id
            for voice in self.list_voices()
        }

        if voice_id not in available_ids:
            raise SpeechError(
                "Voice ID không tồn tại. "
                "Dùng --list-voices để xem các giọng đã cài."
            )

        errors: list[str] = []
        completed: list[bool] = []

        error_token = self._engine.connect(
            "error",
            lambda name, exception: errors.append(
                str(exception)
            ),
        )

        finished_token = self._engine.connect(
            "finished-utterance",
            lambda name, finished: completed.append(
                bool(finished)
            ),
        )

        try:
            self._engine.setProperty("voice", voice_id)
            self._engine.setProperty("rate", rate)
            self._engine.setProperty("volume", 1.0)

            self._engine.say(text)
            self._engine.runAndWait()

            if errors:
                raise SpeechError("; ".join(errors))

            if not completed or not all(completed):
                raise SpeechError(
                    "TTS không xác nhận đã phát hết câu lệnh."
                )
        except SpeechError:
            raise
        except Exception as exc:
            raise SpeechError(
                f"Lỗi phát âm thanh: {exc}"
            ) from exc
        finally:
            self._engine.disconnect(error_token)
            self._engine.disconnect(finished_token)

    def close(self) -> None:
        self._engine.stop()