"""
gestures.py — authored poses, easing, emotion motions
Joint order: _1 .. _6 (degrees)
"""
from pathlib import Path
import os
import time

from dotenv import load_dotenv
from cyberwave import Cyberwave

load_dotenv(Path(__file__).resolve().parent / ".env")

JOINTS = ["_1", "_2", "_3", "_4", "_5", "_6"]

HOME = [-0.57, -99.99, 68.75, 85.94, -82.51, -10.03]
CURIOUS_A = [-6.88, 10.89, 9.74, -24.64, -30.72, -7.45]
CURIOUS_B = [-6.88, 10.89, 9.74, -24.64, 30.98, -7.45]
SAD = [-6.88, 9.17, -24.64, 95.00, -6.88, -5.73]
NOD_UP = [-6.88, 9.17, -12.61, -30.69, -6.88, -5.73]
NOD_DOWN = [-6.88, 9.17, -12.61, 30.28, -4.58, -5.73]
PEAK = [-1.72, 41.83, -32.09, -19.48, -4.01, -5.73]

_current = list(HOME)


def set_pose_raw(arm, values, settle=0.05):
    global _current
    for j, v in zip(JOINTS, values):
        arm.joints.set(j, float(v), degrees=True)
    _current = [float(v) for v in values]
    time.sleep(settle)


def ease_in_out(alpha: float) -> float:
    alpha = max(0.0, min(1.0, alpha))
    return alpha * alpha * (3.0 - 2.0 * alpha)


def smooth_to(arm, target, duration=1.6, steps=24, easing=True):
    global _current
    start = list(_current)
    target = [float(v) for v in target]
    dt = duration / max(steps, 1)

    for s in range(1, steps + 1):
        alpha = s / steps
        if easing:
            alpha = ease_in_out(alpha)
        mid = [start[i] + alpha * (target[i] - start[i]) for i in range(6)]
        for j, v in zip(JOINTS, mid):
            arm.joints.set(j, v, degrees=True)
        _current = mid
        time.sleep(dt)


def curious_look(arm, cycles=3, half_duration=0.9):
    print("gesture: CURIOUS")
    smooth_to(arm, CURIOUS_A, duration=1.4, steps=20)
    for _ in range(cycles):
        smooth_to(arm, CURIOUS_B, duration=half_duration, steps=16)
        smooth_to(arm, CURIOUS_A, duration=half_duration, steps=16)


def nod(arm, cycles=2, half_duration=0.55):
    print("gesture: NOD")
    smooth_to(arm, NOD_UP, duration=1.0, steps=16)
    for _ in range(cycles):
        smooth_to(arm, NOD_DOWN, duration=half_duration, steps=12)
        smooth_to(arm, NOD_UP, duration=half_duration, steps=12)


def sad_blabber(arm, cycles=6):
    print("gesture: SAD + blabber")
    smooth_to(arm, SAD, duration=1.5, steps=20)
    base = list(SAD)
    for i in range(cycles):
        roll = base[4] + (18 if i % 2 == 0 else -18)
        grip = base[5] + (25 if i % 2 == 0 else -5)
        frame = [base[0], base[1], base[2], base[3], roll, grip]
        smooth_to(arm, frame, duration=0.35, steps=8)


def peak_attention(arm, hold=1.2):
    print("gesture: PEAK (you called me)")
    smooth_to(arm, PEAK, duration=1.4, steps=22)
    time.sleep(hold)


def go_home(arm, duration=1.8, steps=24):
    print("gesture: HOME")
    smooth_to(arm, HOME, duration=duration, steps=steps)


def play_intent(arm, intent: str) -> None:
    """Map LLM intent → gesture. Used by companion_llm.py."""
    intent = (intent or "IDLE").upper().strip()
    if intent == "WAKE":
        peak_attention(arm, hold=1.2)
    elif intent == "CURIOUS":
        curious_look(arm, cycles=2)
    elif intent == "AFFIRM":
        nod(arm, cycles=2)
    elif intent == "SAD":
        sad_blabber(arm, cycles=5)
    elif intent == "RELAX":
        go_home(arm)
    else:
        print("gesture: IDLE (no motion)")


def connect_arm(warmup_s=4.0):
    """
    Create Cyberwave client + arm twin (playground only).
    Returns (cw, arm).
    """
    twin_id = os.getenv("CYBERWAVE_TWIN_ID")
    if not os.getenv("CYBERWAVE_API_KEY") or not twin_id:
        raise SystemExit("Need CYBERWAVE_API_KEY and CYBERWAVE_TWIN_ID in .env")

    cw = Cyberwave()
    cw.affect("playground")  # only mode we use

    arm = cw.twin(twin_id=twin_id)
    print("joints:", arm.joints.list())
    print(f"warmup {warmup_s}s...")
    time.sleep(warmup_s)
    set_pose_raw(arm, HOME, settle=0.3)
    time.sleep(0.4)
    return cw, arm


def main():
    """Optional: gesture-only smoke test."""
    cw, arm = connect_arm()
    peak_attention(arm, hold=1.5)
    curious_look(arm, cycles=2)
    nod(arm, cycles=2)
    sad_blabber(arm, cycles=4)
    go_home(arm)
    cw.disconnect()
    print("done")


if __name__ == "__main__":
    main()