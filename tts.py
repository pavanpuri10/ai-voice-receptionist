"""
Text-to-speech using pyttsx3 -- fully offline, free, no API key.

Note: voice quality is robotic compared to cloud TTS. If you want a more
natural voice later (still free), swap this module for Piper TTS
(https://github.com/rhasspy/piper) -- the rest of the app doesn't need to change,
just call piper instead of pyttsx3 inside `speak()`.
"""

import pyttsx3

from config import TTS_RATE, TTS_VOLUME

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", TTS_RATE)
        _engine.setProperty("volume", TTS_VOLUME)
    return _engine


def speak(text: str) -> None:
    """Speak the given text out loud and print it for logging."""
    print(f"[receptionist] {text}")
    engine = _get_engine()
    engine.say(text)
    engine.runAndWait()
