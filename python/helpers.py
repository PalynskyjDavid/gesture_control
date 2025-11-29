import math
import cv2
import mediapipe as mp
import json
import os
import time

mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles


# ---------- vector & geometry ----------
def vec_sub(a, b):
    return (a.x - b.x, a.y - b.y, a.z - b.z)


def vec_len(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def dist(a, b):
    """Euclidean distance in normalized coordinates between two landmarks."""
    return vec_len(vec_sub(a, b))


def angle(a, b, c):
    """Angle (degrees) at b for points a-b-c."""
    ab = vec_sub(a, b)
    cb = vec_sub(c, b)
    dot = ab[0] * cb[0] + ab[1] * cb[1] + ab[2] * cb[2]
    mag1 = vec_len(ab)
    mag2 = vec_len(cb)
    if mag1 * mag2 == 0:
        return 0.0
    v = dot / (mag1 * mag2)
    v = max(min(v, 1.0), -1.0)
    return math.degrees(math.acos(v))


def is_curled(lm, tip, pip, mcp):
    """
    Heuristic curl test; assumes normalized coordinates where y increases downwards.
    Returns True if tip.y > pip.y > mcp.y.
    """
    return lm[tip].y > lm[pip].y and lm[pip].y > lm[mcp].y


def wrist_position(lm):
    """Return wrist dict for JSON."""
    return {"x": lm[0].x, "y": lm[0].y, "z": lm[0].z}


# ---------- debug drawing ----------
def draw_hand_debug(frame, hand_data, offset_y=0):
    """
    Draw landmarks + text overlay for a single hand.
    offset_y shifts text block vertically (useful for multiple hands).
    """
    h, w, _ = frame.shape
    if hand_data.raw_landmarks is not None:
        mp_drawing.draw_landmarks(
            frame,
            hand_data.raw_landmarks,
            mp.solutions.hands.HAND_CONNECTIONS,
            mp_styles.get_default_hand_landmarks_style(),
            mp_styles.get_default_hand_connections_style(),
        )

    x0, y0 = 10, 30 + offset_y
    dy = 20
    info = [
        f"hand: {hand_data.handedness}",
        f"gesture: {hand_data.gesture}",
        f"visible: {hand_data.visible}",
        f"conf: {hand_data.confidence:.2f}",
        f"pinch: {hand_data.pinch_distance:.3f}",
        f"thumb_angle: {hand_data.thumb_angle:.1f}",
        f"curls: {hand_data.curls}",
        f"curled: {hand_data.curled_count}",
        f"extended: {hand_data.extended_count}",
        f"wrist: ({hand_data.wrist['x']:.2f},{hand_data.wrist['y']:.2f})",
        f"t: {hand_data.timestamp:.2f}, dt:{hand_data.dt:.3f}",
    ]
    for i, line in enumerate(info):
        cv2.putText(
            frame,
            line,
            (x0, y0 + i * dy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )


def load_config(path="config.json"):
    if not os.path.exists(path):
        print(f"[PY] config '{path}' not found, using defaults.")
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print("[PY] Failed to load config:", e)
        return {}


class ConfigWatcher:
    """
    Watches a JSON config file and reloads it when the file changes.
    Usage:
        watcher = ConfigWatcher("config.json")
        cfg = watcher.get_config()        # initial load
        # later:
        cfg = watcher.check_reload()      # returns new cfg or same dict
    """

    def __init__(self, path="config.json"):
        self.path = path
        self._cfg = {}
        self._mtime = 0.0
        self._last_checked = 0.0
        self._min_check_interval = 0.5  # seconds between checks
        self._load()  # load now

    def _load(self):
        try:
            if not os.path.exists(self.path):
                self._cfg = {}
                self._mtime = 0.0
                return
            m = os.path.getmtime(self.path)
            with open(self.path, "r", encoding="utf-8") as f:
                self._cfg = json.load(f)
            self._mtime = m
        except Exception as e:
            print("[ConfigWatcher] failed to load config:", e)
            self._cfg = {}

    def get_config(self):
        return self._cfg

    def check_reload(self):
        """
        Call frequently (cheap). Will only stat the file every _min_check_interval seconds.
        Returns current config (reloaded if changed).
        """
        now = time.time()
        if now - self._last_checked < self._min_check_interval:
            return self._cfg
        self._last_checked = now

        try:
            if not os.path.exists(self.path):
                # file missing -> keep existing config
                return self._cfg
            m = os.path.getmtime(self.path)
            if m != self._mtime:
                print("[ConfigWatcher] Detected config.json change, reloading...")
                self._load()
        except Exception as e:
            print("[ConfigWatcher] check_reload error:", e)

        return self._cfg
