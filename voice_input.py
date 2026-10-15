import json
import os
import queue
import threading
import pyaudio
from vosk import Model, KaldiRecognizer
from config import COMMAND_MAP

NUMBER_MAP = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "hundred": 100
}


class VoiceController:
    """open-vocabulary voice recognition with context-aware parsing."""

    def __init__(self, model_path: str = "model"):
        self.command_queue = queue.Queue()
        self.last_transcript = "Say: 'go to letter a', 'move to sign b', or 'pause game'"
        self.is_running = False
        self._worker_thread = None

        self._audio = pyaudio.PyAudio()
        self._stream = None

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Vosk model directory '{model_path}' not found! "
                "Ensure vosk-model-small-en-us is extracted into a folder named 'model'."
            )
        self._model = Model(model_path)

        self._sample_rate = 16000
        self._recognizer = KaldiRecognizer(self._model, self._sample_rate)
        self._recognizer.SetWords(False)

        self.available_microphones = self._discover_microphones()
        self.selected_index = 0

    def _discover_microphones(self) -> list[tuple[int, str]]:
        devices = []
        try:
            for idx in range(self._audio.get_device_count()):
                info = self._audio.get_device_info_by_index(idx)
                if info.get("maxInputChannels", 0) > 0:
                    devices.append((idx, info.get("name", f"Microphone {idx}")))
        except Exception:
            pass
        return devices if devices else [(None, "Default System Microphone")]

    @property
    def active_mic_name(self) -> str:
        if not self.available_microphones:
            return "No Microphones Detected"
        _, name = self.available_microphones[self.selected_index]
        return name[:32] + ("..." if len(name) > 32 else "")

    def cycle_microphone(self):
        if len(self.available_microphones) > 1:
            self.selected_index = (self.selected_index + 1) % len(self.available_microphones)
            self.last_transcript = f"Switching to: {self.active_mic_name}..."
            self.stop()
            self.start()

    def get_latest_command(self) -> tuple[dict | None, str] | None:
        try:
            return self.command_queue.get_nowait()
        except queue.Empty:
            return None

    def start(self):
        self.is_running = True
        self._worker_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._worker_thread.start()

    def stop(self):
        self.is_running = False
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _stream_loop(self):
        dev_index, _ = self.available_microphones[self.selected_index]
        try:
            self._stream = self._audio.open(
                format=pyaudio.paInt16, channels=1, rate=self._sample_rate,
                input=True, input_device_index=dev_index, frames_per_buffer=2048
            )
            self._stream.start_stream()
        except Exception as err:
            self.last_transcript = f"Audio init error: {err}"
            return

        while self.is_running:
            try:
                data = self._stream.read(1024, exception_on_overflow=False)
                if len(data) == 0:
                    continue

                if self._recognizer.AcceptWaveform(data):
                    res = json.loads(self._recognizer.Result())
                    phrase = res.get("text", "").strip()
                    if phrase:
                        self.last_transcript = f"Heard: '{phrase}'"
                        cmd_dict = self._parse_full_phrase(phrase)
                        self.command_queue.put((cmd_dict, phrase))
            except Exception:
                continue

    @staticmethod
    def _extract_distance(words: list[str]) -> int | None:
        total, current = 0, 0
        found_num = False
        for w in words:
            if w in NUMBER_MAP:
                found_num = True
                val = NUMBER_MAP[w]
                if val == 100:
                    if current == 0: current = 1
                    current *= 100
                else:
                    current += val
            elif w.isdigit():
                found_num = True
                current += int(w)
            else:
                total += current
                current = 0
        total += current
        return total if found_num else None

    @staticmethod
    def _parse_full_phrase(phrase: str) -> dict | None:
        words = phrase.split()
        distance = VoiceController._extract_distance(words)
        action = None

        if any(w in ("exit", "end", "quit") for w in words):
            action = "exit_game"
        elif "pause" in words:
            action = "pause_game"
        elif any(w in ("resume", "play", "unpause") for w in words):
            action = "resume_game"
        elif any(w in ("start", "back", "reset", "home") for w in words):
            action = "to_start"

        else:
            # Context-Aware Anchor check: prevents "go left a block" from targeting Sign A.
            is_targeting_sign = False
            # Check for explicit keywords and homophones for "B"
            if any(w in ("sign", "target", "red", "blue", "b", "bee", "be", "letter") for w in words):
                is_targeting_sign = True
            # Check if "a" is used specifically as a destination
            elif "a" in words and ("to" in words or words[-1] == "a"):
                is_targeting_sign = True

            if is_targeting_sign:
                target = "sign_a"
                # Catch actual "b" and common transcript errors for B
                if any(w in ("b", "bee", "be", "blue") for w in words):
                    target = "sign_b"

                if any(w in ("left", "west") for w in words):
                    action = f"{target}_left"
                elif any(w in ("right", "east") for w in words):
                    action = f"{target}_right"
                elif any(w in ("above", "top", "over", "up", "north") for w in words):
                    action = f"{target}_above"
                elif any(w in ("below", "under", "bottom", "down", "south") for w in words):
                    action = f"{target}_below"
                else:
                    action = f"{target}_center"

            else:
                # Standard Directional Grid Steps
                for w in words:
                    if w in ("up", "down", "left", "right", "north", "south", "east", "west"):
                        action = COMMAND_MAP.get(w, w)
                        break
                    if w in ("stop", "halt", "wait"):
                        action = "stop"
                        break

        if action:
            return {"action": action, "distance": distance}
        return None