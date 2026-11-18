"""Local energy/silence endpointing; no network or background listener."""
from array import array
from dataclasses import dataclass
import io
import math
import threading
import wave

from .speech import SpeechInputError
from .control import check_stop


@dataclass
class SilenceEndpoint:
    threshold: float = 500
    silence_seconds: float = 1.2
    idle_seconds: float = 8
    max_seconds: float = 20
    elapsed: float = 0
    voiced: float = 0
    quiet: float = 0

    def feed(self, rms: float, seconds: float) -> str | None:
        self.elapsed += seconds
        if rms >= self.threshold:
            self.voiced += seconds
            self.quiet = 0
        else:
            self.quiet += seconds
        # Never submit an utterance cut off by a duration limit.
        if self.elapsed >= self.max_seconds:
            return 'too_long'
        if self.voiced >= .25 and self.quiet >= self.silence_seconds:
            return 'complete'
        if self.voiced < .25 and self.elapsed >= self.idle_seconds:
            return 'no_speech'
        return None


def record_until_silence(*, threshold=500, silence_seconds=1.2, stop_event=None) -> bytes:
    import sounddevice as sd

    check_stop(stop_event)
    if not 1 <= threshold <= 32767 or not .5 <= silence_seconds <= 3:
        raise ValueError('Invalid endpoint settings')
    rate = int(sd.query_devices(None, 'input')['default_samplerate'])
    endpoint = SilenceEndpoint(threshold=threshold, silence_seconds=silence_seconds)
    chunks = []
    done = threading.Event()
    outcome = []

    def callback(indata, frames, time_info, status):
        try:
            if status:
                outcome.append('audio_error')
                done.set()
                raise sd.CallbackStop
            raw = bytes(indata)
            samples = array('h', raw)
            rms = math.sqrt(sum(x * x for x in samples) / max(1, len(samples)))
            chunks.append(raw)
            decision = endpoint.feed(rms, frames / rate)
            if decision:
                outcome.append(decision)
                done.set()
                raise sd.CallbackStop
        except sd.CallbackStop:
            raise
        except Exception:
            outcome.append('audio_error')
            done.set()
            raise sd.CallbackAbort

    print('Đang nghe… nói yêu cầu rồi ngừng 1–3 giây. Ctrl+C để dừng.', flush=True)
    with sd.RawInputStream(samplerate=rate, channels=1, dtype='int16',
                           blocksize=max(1, int(rate * .05)), callback=callback):
        # Polling permits Ctrl+C on Windows; hard deadline covers stalled devices.
        import time
        deadline = time.monotonic() + endpoint.max_seconds + 2
        while not done.wait(.05):
            check_stop(stop_event)
            if time.monotonic() >= deadline:
                raise SpeechInputError('Microphone timeout; không gửi audio.', code='audio_timeout')
    check_stop(stop_event)
    if outcome != ['complete']:
        reason = {'no_speech': 'Không nghe rõ lời nói trong 8 giây.',
                  'too_long': 'Câu nói chạm giới hạn 20 giây.',
                  'audio_error': 'Microphone có lỗi.'}.get(outcome[0] if outcome else '', 'Thu âm bị ngắt.')
        raise SpeechInputError(reason + ' Không gửi audio, không tự thử lại.',
                               code=outcome[0] if outcome else 'audio_error')
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b''.join(chunks))
    return output.getvalue()
