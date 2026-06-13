import os
import struct
import wave
import math
import random
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl


SOUNDS_DIR = os.path.join(os.path.expanduser("~"), ".pomodoro_focus", "sounds")

SOUND_TYPES = {
    "rain": "雨声",
    "cafe": "咖啡馆",
    "forest": "森林",
}

SAMPLE_RATE = 44100
DURATION = 30


def _ensure_sounds_dir():
    os.makedirs(SOUNDS_DIR, exist_ok=True)


def _write_wav(path, samples):
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        data = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
            for s in samples
        )
        wf.writeframes(data)


def _generate_rain(path):
    random.seed(42)
    n = SAMPLE_RATE * DURATION
    samples = [0.0] * n
    for i in range(n):
        val = random.gauss(0, 0.15)
        if random.random() < 0.002:
            val += random.gauss(0, 0.5)
        if i > 0:
            samples[i] = 0.7 * samples[i - 1] + 0.3 * val
        else:
            samples[i] = val
    _write_wav(path, samples)


def _generate_cafe(path):
    random.seed(123)
    n = SAMPLE_RATE * DURATION
    samples = [0.0] * n
    low_noise = [random.gauss(0, 0.05) for _ in range(n)]
    for i in range(1, n):
        low_noise[i] = 0.95 * low_noise[i - 1] + 0.05 * low_noise[i]
    chatter = [0.0] * n
    for i in range(n):
        freq = 200 + 50 * math.sin(2 * math.pi * i / SAMPLE_RATE * 0.3)
        chatter[i] = 0.03 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
        chatter[i] += random.gauss(0, 0.02)
    clink_interval = SAMPLE_RATE * 5
    for start in range(0, n, clink_interval):
        offset = random.randint(-SAMPLE_RATE, SAMPLE_RATE)
        pos = start + offset
        if 0 <= pos < n:
            for j in range(min(800, n - pos)):
                t = j / SAMPLE_RATE
                chatter[pos + j] += 0.1 * math.sin(2 * math.pi * 3000 * t) * math.exp(-t * 20)
    for i in range(n):
        samples[i] = low_noise[i] + chatter[i]
    _write_wav(path, samples)


def _generate_forest(path):
    random.seed(456)
    n = SAMPLE_RATE * DURATION
    samples = [0.0] * n
    wind = [0.0] * n
    for i in range(n):
        wind[i] = random.gauss(0, 0.04)
        if i > 0:
            wind[i] = 0.97 * wind[i - 1] + 0.03 * wind[i]
    chirp_positions = []
    pos = SAMPLE_RATE * 2
    while pos < n:
        chirp_positions.append(pos)
        pos += random.randint(SAMPLE_RATE, SAMPLE_RATE * 4)
    for cp in chirp_positions:
        freq = random.uniform(2000, 4000)
        chirp_len = random.randint(500, 2000)
        for j in range(min(chirp_len, n - cp)):
            t = j / SAMPLE_RATE
            envelope = math.sin(math.pi * j / chirp_len)
            samples[cp + j] += 0.06 * math.sin(2 * math.pi * freq * t) * envelope
            freq += random.uniform(-100, 100)
    for i in range(n):
        samples[i] += wind[i]
    _write_wav(path, samples)


_GENERATORS = {
    "rain": _generate_rain,
    "cafe": _generate_cafe,
    "forest": _generate_forest,
}


def ensure_sound_files():
    _ensure_sounds_dir()
    for name, gen_func in _GENERATORS.items():
        path = os.path.join(SOUNDS_DIR, f"{name}.wav")
        if not os.path.exists(path):
            gen_func(path)


def get_sound_path(sound_type):
    return os.path.join(SOUNDS_DIR, f"{sound_type}.wav")


class AudioPlayer:
    def __init__(self):
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.5)
        self._current_type = None
        self._player.loopsChanged.connect(self._on_loops_changed)
        self._player.setLoops(QMediaPlayer.Loops.Infinite)

    def _on_loops_changed(self):
        pass

    def play(self, sound_type):
        if sound_type not in SOUND_TYPES:
            return
        path = get_sound_path(sound_type)
        if not os.path.exists(path):
            return
        if self._current_type == sound_type and self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return
        self._current_type = sound_type
        self._player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        self._player.play()

    def stop(self):
        self._player.stop()
        self._current_type = None

    def pause(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()

    def resume(self):
        if self._current_type is not None and \
           self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()

    def set_volume(self, volume):
        self._audio_output.setVolume(max(0.0, min(1.0, volume)))

    def get_volume(self):
        return self._audio_output.volume()

    def is_playing(self):
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def current_sound(self):
        return self._current_type
