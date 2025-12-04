"""
Unified entry point for the gesture-tracking backends.

Usage examples:
    python gesture_server.py --mode full    # default, rich MediaPipe pipeline
    python gesture_server.py --mode simple  # legacy ZeroMQ pinch/fist/open demo
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY_DIR = ROOT / "python"
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))


def run_simple_mode() -> None:
    """Run the original one-hand ZeroMQ publisher for smoke testing."""
    import math
    import time

    import cv2
    import mediapipe as mp
    import zmq

    mp_hands = mp.solutions.hands.Hands(
        model_complexity=0,
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:5555")

    cap = cv2.VideoCapture(0)

    def dist(a, b):
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

    print("[PY] Running legacy simple server (ZeroMQ). Press ESC to stop.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = mp_hands.process(frame_rgb)

            gesture = None

            if result.multi_hand_landmarks:
                hand = result.multi_hand_landmarks[0].landmark

                thumb = hand[4]
                index = hand[8]
                d = dist(thumb, index)

                if d < 0.05:
                    gesture = "pinch"
                elif hand[8].y > hand[6].y and hand[12].y > hand[10].y:
                    gesture = "fist"
                else:
                    gesture = "open_palm"

            if gesture:
                socket.send_string(gesture)

            cv2.imshow("MediaPipe Hands", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        cap.release()
        socket.close()
        context.term()
        cv2.destroyAllWindows()


def run_full_mode() -> None:
    """Delegate to the threaded MediaPipe + TCP JSON publisher (python/main_loop)."""
    from main_loop import main as run_main_loop

    prev_cwd = os.getcwd()
    os.chdir(str(PY_DIR))
    try:
        run_main_loop()
    finally:
        os.chdir(prev_cwd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gesture server launcher")
    parser.add_argument(
        "--mode",
        choices=("full", "simple"),
        default="full",
        help="Select backend: 'full' runs python/main_loop.py, 'simple' keeps the legacy ZeroMQ demo.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "simple":
        run_simple_mode()
    else:
        run_full_mode()


if __name__ == "__main__":
    main()
