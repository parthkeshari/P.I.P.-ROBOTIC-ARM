"""stt.py — record mic audio → Groq Whisper → text"""
from pathlib import Path
import os
import tempfile
import wave

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).resolve().parent / ".env")

SAMPLE_RATE = 16000  # Whisper-friendly
CHANNELS = 1
DEFAULT_SECONDS = float(os.getenv("STT_SECONDS", "4"))


def record_seconds(seconds: float = DEFAULT_SECONDS) -> np.ndarray:
    """Record mono float32 audio from the default mic."""
    print(f"Recording {seconds:.1f}s — speak now...")
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()
    print("Recording done.")
    return audio.reshape(-1)


def _write_wav(path: Path, audio: np.ndarray) -> None:
    # float32 -1..1 → int16 PCM
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())


def transcribe(audio: np.ndarray) -> str:
    """Send wav to Groq Whisper, return transcript text."""
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    path = Path(tempfile.mkstemp(suffix=".wav")[1])
    try:
        _write_wav(path, audio)
        with open(path, "rb") as f:
            result = client.audio.transcriptions.create(
                file=f,
                model="whisper-large-v3-turbo",  # or whisper-large-v3
                language="en",  # drop this if you want auto language
            )
        text = (result.text or "").strip()
        return text
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def listen_once(seconds: float = DEFAULT_SECONDS) -> str:
    audio = record_seconds(seconds)
    text = transcribe(audio)
    print(f"STT: {text!r}")
    return text