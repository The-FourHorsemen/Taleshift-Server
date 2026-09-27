"""
recorder.py
Audio recording module for Taleshift's reading-capture pipeline.

Records microphone audio while a learner reads aloud, and saves the result
as a WAV file suitable for downstream ASR (16kHz mono by default, which is
the standard input rate for most ASR models).

Requires:
    pip install sounddevice soundfile numpy
"""

import queue
import threading
import time
from pathlib import Path
from typing import Optional, List

import numpy as np
import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    """
    Records audio on a background thread, buffering chunks until stop() is
    called, then writes the buffered audio to a WAV file.

    Usage (manual start/stop - e.g. triggered by UI buttons):
        recorder = AudioRecorder(samplerate=16000, channels=1)
        recorder.start()
        ...  # learner reads aloud
        recorder.stop()
        path = recorder.save("learner_reading.wav")

    Usage (context manager, with an optional safety ceiling):
        with AudioRecorder() as recorder:
            recorder.start(max_seconds=180)  # auto-stops after 3 min if stop() is never called
            ...  # wait for some "reading finished" signal
            recorder.stop()
            recorder.save("session_001.wav")
    """

    def __init__(
        self,
        samplerate: int = 16000,
        channels: int = 1,
        device: Optional[int] = None,
        dtype: str = "int16",
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.device = device
        self.dtype = dtype

        self._queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._recording = False
        self._frames: List[np.ndarray] = []
        self._lock = threading.Lock()
        self._start_time: Optional[float] = None
        self._max_seconds: Optional[float] = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[AudioRecorder] status: {status}")
        self._queue.put(indata.copy())

        if self._max_seconds is not None and self._start_time is not None:
            if time.monotonic() - self._start_time >= self._max_seconds:
                raise sd.CallbackStop()

    def start(self, max_seconds: Optional[float] = None) -> None:
        """
        Begin recording with no fixed length by default - it keeps going
        until stop() is called. Pass max_seconds as an optional safety
        ceiling - leave it None for no limit.
        """
        with self._lock:
            if self._recording:
                raise RuntimeError("Recording already in progress")
            self._frames = []
            self._max_seconds = max_seconds
            self._start_time = time.monotonic()
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                device=self.device,
                dtype=self.dtype,
                callback=self._callback,
            )
            self._stream.start()
            self._recording = True

    def stop(self) -> None:
        """Stop recording and drain any buffered audio into memory."""
        with self._lock:
            if not self._recording:
                return
            self._stream.stop()
            self._stream.close()
            self._recording = False

        while not self._queue.empty():
            self._frames.append(self._queue.get())

    def save(self, filepath: str) -> str:
        """
        Write the recorded audio to a WAV file (16-bit PCM).
        Returns the path written to. Call after stop().
        """
        if not self._frames:
            raise RuntimeError("No audio recorded - call start() then stop() first")

        audio = np.concatenate(self._frames, axis=0)
        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        sf.write(str(out_path), audio, self.samplerate, subtype="PCM_16")
        return str(out_path)

    def record_fixed_duration(self, seconds: float, filepath: str) -> str:
        """Convenience method for a timed recording (blocks for `seconds`)."""
        audio = sd.rec(
            int(seconds * self.samplerate),
            samplerate=self.samplerate,
            channels=self.channels,
            dtype=self.dtype,
            device=self.device,
        )
        sd.wait()
        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), audio, self.samplerate, subtype="PCM_16")
        return str(out_path)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @staticmethod
    def list_input_devices():
        return sd.query_devices()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._recording:
            self.stop()


if __name__ == "__main__":
    print("Available input devices:")
    print(AudioRecorder.list_input_devices())

    recorder = AudioRecorder(samplerate=16000, channels=1)

    recorder.start()
    input("Recording... press Enter to stop.\n")
    recorder.stop()

    path = recorder.save("test_recording.wav")
    print(f"Saved to {path}")