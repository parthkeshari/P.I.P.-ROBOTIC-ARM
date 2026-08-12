"""tts.py — speak text via edge-tts"""
import asyncio
import tempfile
from pathlib import Path

import edge_tts
import pygame

# pick any edge voice; change later if you want
VOICE = "en-GB-RyanNeural"


async def _synthesize(text: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(out_path))


def speak(text: str, block: bool = False) -> None:
    """
    Speak `text`.
    block=False → return after starting playback setup (we still wait for file gen);
                 for true background audio + motion, we generate then play non-blocking.
    """
    if not text or not text.strip():
        return

    text = text.strip()
    print(f"TTS: {text}")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        path = Path(f.name)

    try:
        asyncio.run(_synthesize(text, path))

        pygame.mixer.init()
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play()

        if block:
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
    finally:
        # leave file cleanup simple; OS temp dir is fine for V1
        pass


def stop_speech() -> None:
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass