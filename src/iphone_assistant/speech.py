import io
import json
import os
import wave
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SpeechInputError(RuntimeError):
    pass


def record_wav(
    *,
    device: int | None = None,
    max_seconds: int = 30,
) -> bytes:
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise SpeechInputError(
            'Thiếu sounddevice. Cài bằng: '
            'python -m pip install -e ".[windows,speech]"'
        ) from exc

    if not 1 <= max_seconds <= 60:
        raise SpeechInputError(
            "Giới hạn thu âm phải từ 1 đến 60 giây."
        )

    chunks: list[bytes] = []
    warnings: list[str] = []
    sample_count = 0
    reached_limit = False

    try:
        info = sd.query_devices(device, "input")
        sample_rate = int(info["default_samplerate"])

        max_frames = sample_rate * max_seconds

        def callback(indata, frames, time_info, status):
            nonlocal sample_count, reached_limit

            if status:
                warnings.append(str(status))

            remaining = max_frames - sample_count
            accepted = min(frames, remaining)

            if accepted > 0:
                # Mono int16: hai byte cho mỗi sample.
                chunks.append(bytes(indata)[: accepted * 2])
                sample_count += accepted

            if sample_count >= max_frames:
                reached_limit = True
                raise sd.CallbackStop

        input(
            "Nhấn Enter để bắt đầu thu "
            "(Ctrl+C để hủy)..."
        )

        with sd.RawInputStream(
            device=device,
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            callback=callback,
        ):
            input(
                f"Đang thu, tối đa {max_seconds} giây. "
                "Nhấn Enter để kết thúc...\n"
            )

    except (KeyboardInterrupt, EOFError):
        raise
    except Exception as exc:
        raise SpeechInputError(
            f"Không thu được microphone: {exc}"
        ) from exc

    if reached_limit:
        raise SpeechInputError(
            "Đã chạm giới hạn thời lượng. "
            "Không gửi bản thu bị giới hạn; "
            "hãy chạy lại và nói câu ngắn hơn."
        )

    if warnings:
        raise SpeechInputError(
            "Luồng microphone có cảnh báo, "
            "không gửi audio: "
            + "; ".join(dict.fromkeys(warnings))
        )

    if sample_count < sample_rate // 4:
        raise SpeechInputError(
            "Bản thu quá ngắn. Hãy nói rồi mới kết thúc."
        )

    output = io.BytesIO()

    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(chunks))

    return output.getvalue()


def transcribe_vietnamese(wav_audio: bytes) -> str:
    api_key = os.environ.get(
        "DEEPGRAM_API_KEY", ""
    ).strip()

    if not api_key:
        raise SpeechInputError(
            "Chưa đặt biến môi trường DEEPGRAM_API_KEY."
        )

    params = urlencode(
        {
            "model": "nova-3",
            "language": "vi",
            "punctuate": "false",
            "smart_format": "false",
        }
    )

    request = Request(
        url=f"https://api.deepgram.com/v1/listen?{params}",
        data=wav_audio,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "audio/wav",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)

    except HTTPError as exc:
        messages = {
            400: "Deepgram từ chối định dạng hoặc tham số.",
            401: "Deepgram API key không hợp lệ.",
            402: "Kiểm tra số dư hoặc thanh toán Deepgram.",
            403: "API key không có quyền thực hiện yêu cầu.",
            429: "Deepgram đang giới hạn yêu cầu.",
        }

        message = messages.get(
            exc.code,
            "Deepgram trả về lỗi.",
        )

        raise SpeechInputError(
            f"{message} HTTP {exc.code}."
        ) from exc

    except (URLError, TimeoutError, OSError) as exc:
        raise SpeechInputError(
            "Không kết nối được Deepgram hoặc đã hết "
            "thời gian chờ. Không tự gửi lại audio."
        ) from exc

    except (ValueError, UnicodeError) as exc:
        raise SpeechInputError(
            "Phản hồi Deepgram không phải JSON hợp lệ."
        ) from exc

    try:
        transcript = payload["results"]["channels"][0][
            "alternatives"
        ][0]["transcript"]

        if not isinstance(transcript, str):
            raise TypeError("Transcript không phải chuỗi.")

        transcript = transcript.strip()

    except (KeyError, IndexError, TypeError) as exc:
        raise SpeechInputError(
            "Phản hồi Deepgram thiếu transcript."
        ) from exc

    if not transcript:
        raise SpeechInputError(
            "Không nhận được lời nói. "
            "Kiểm tra microphone hoặc nói rõ hơn."
        )

    return transcript