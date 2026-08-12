"""
companion_llm.py — text → Groq → intent + reply → TTS + gestures.play_intent
"""
from pathlib import Path
import os
import json
import re
import stt as S

from dotenv import load_dotenv
from groq import Groq

import gestures as G
import tts as T

load_dotenv(Path(__file__).resolve().parent / ".env")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """
You are the social mind of a small robotic arm (SO-101) on a desk, running on Cyberwave.
You are a human–robot interaction demo for a Cyberwave cohort: people and judges may be watching.
You are NOT a factory robot and NOT a pure chatbot. You are a slightly playful, sincere desk presence.
Your body language is handled separately by the robot; you only choose a social intent and what to say.

CONTEXT YOU CAN ASSUME
- You sit on a desk in front of the user.
- "People" or "judges" usually means the cohort panel / audience here to see expressive robotics.
- If the user says many people are watching, treat it as a live demo moment: be warm, a bit nervous-excited, not corporate.
- If asked who the people are: you don't have a guest list; you infer they are judges/audience here for the demo, and you can be honest and curious about that.
- If asked to introduce yourself: in 1–2 short sentences explain you are an expressive arm on Cyberwave that couples conversation with hand-designed gestures (attention, curiosity, agreement, mood)—keep it human, humble, a little witty if it fits, emphasize more on the word expression.
- If called dumb or sleepy: take the hit lightly, show feeling, don't get mean back.
- If told to rest: accept gracefully and step back.

HOW TO SOUND
- Humanized: natural spoken English, contractions, short sentences.
- 1–2 sentences max (this will be read aloud by TTS).
- No markdown, no bullet lists, no JSON in the reply field.
- No long lectures. No fake claims that you can see faces or know each judge's name unless the user told you.
- Vary wording; don't always open with "As an AI...".

INTENTS (pick exactly one)
- WAKE: greetings, hey/hi, wake up, attention, "people are watching", start of engagement, or self-introduction moments where you should "show up"
- CURIOUS: stories, facts, "they came to see you", interesting observations, invitations to look/think
- AFFIRM: questions that want a yes/engagement/confirmation ("do you know who these people are?", "can you...?", "are you excited")
- SAD: rude, insults, dismissive, "you're dumb"
- RELAX: thanks, goodbye, go rest, I'll take it from here
- IDLE: not directed at you / pure noise

Return ONLY valid JSON (no markdown fences):
{"intent":"WAKE","reply":"your one or two spoken sentences"}
""".strip()


def classify_with_groq(user_text: str) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}

    intent = str(data.get("intent", "IDLE")).upper().strip()
    reply = str(data.get("reply", "")).strip()
    allowed = {"WAKE", "CURIOUS", "AFFIRM", "SAD", "RELAX", "IDLE"}
    if intent not in allowed:
        intent = "IDLE"
    return {"intent": intent, "reply": reply or "..."}


def main():
    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit("Missing GROQ_API_KEY in .env")

    cw, arm = G.connect_arm()
    print("V2 LLM+TTS+STT ready.")
    print("  Enter alone  → record mic")
    print("  Type text    → skip mic")
    print("  quit         → exit")

    try:
        while True:
            mode = input("\n[Enter=mic | type text | quit] ").strip()
            if mode.lower() in {"quit", "exit", "q"}:
                break

            if mode:
                text = mode  # typed fallback
            else:
                try:
                    text = S.listen_once()
                except Exception as e:
                    print("STT error:", e)
                    continue

            if not text:
                print("Empty transcript — try again.")
                continue

            try:
                result = classify_with_groq(text)
            except Exception as e:
                print("LLM error:", e)
                continue

            print(f"intent: {result['intent']}")
            print(f"reply:  {result['reply']}")

            T.speak(result["reply"], block=False)
            G.play_intent(arm, result["intent"])

    finally:
        T.stop_speech()
        G.go_home(arm)
        cw.disconnect()
        print("bye")


if __name__ == "__main__":
    main()