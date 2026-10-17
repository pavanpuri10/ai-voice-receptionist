"""
Speech-to-text using faster-whisper, running fully locally (no API, no cost).
Records from your default microphone until it detects a pause in speech.
"""

import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from config import (
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    SAMPLE_RATE,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    MAX_RECORD_SECONDS,
)

_model = None


def _get_model():
    global _model
    if _model is None:
        print("[stt] Loading Whisper model (first run may take a moment)...")
        _model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
    return _model


def record_until_silence() -> np.ndarray:
    """Record audio from the mic until the patient stops speaking (or max time reached)."""
    print("[stt] Listening... (speak now)")
    block_duration = 0.1  # seconds
    block_size = int(SAMPLE_RATE * block_duration)
    silence_blocks_needed = int(SILENCE_DURATION / block_duration)

    audio_chunks = []
    silent_blocks = 0
    started_speaking = False
    start_time = time.time()

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
        while True:
            block, _ = stream.read(block_size)
            audio_chunks.append(block.copy())
            volume = np.abs(block).mean()

            if volume > SILENCE_THRESHOLD:
                started_speaking = True
                silent_blocks = 0
            elif started_speaking:
                silent_blocks += 1

            elapsed = time.time() - start_time
            if elapsed > MAX_RECORD_SECONDS:
                break
            if started_speaking and silent_blocks >= silence_blocks_needed:
                break

    audio = np.concatenate(audio_chunks, axis=0).flatten()
    return audio


def transcribe(audio: np.ndarray) -> str:
    """Convert recorded audio (int16 numpy array) to text."""
    audio_float = audio.astype(np.float32) / 32768.0
    model = _get_model()
    segments, _ = model.transcribe(audio_float, language="en")
    text = " ".join(seg.text.strip() for seg in segments)
    return text.strip()


def listen() -> str:
    """Record from the mic and return the transcribed text."""
    audio = record_until_silence()
    text = transcribe(audio)
    print(f"[stt] Heard: {text!r}")
    return text
