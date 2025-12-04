import math
import cv2
import mediapipe as mp
import json
import os
import time

from Angles import (
    FINGER_JOINTS,
    FingerAngleBuffer,
    compute_smoothed_finger_angles,
)

mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles


# ---------- vector & geometry ----------
def vec_sub(a, b):
    return (a.x - b.x, a.y - b.y, a.z - b.z)


def vec_len(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def clamp01(v):
    return max(0.0, min(1.0, v))


def dist(a, b):
    """Euclidean distance in normalized coordinates between two landmarks."""
    return vec_len(vec_sub(a, b))


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def normalize(v):
    length = vec_len(v)
    if length <= 1e-6:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def angle(a, b, c):
    """Angle (degrees) at b for points a-b-c."""
    ab = vec_sub(a, b)
    cb = vec_sub(c, b)
    mag1 = vec_len(ab)
    mag2 = vec_len(cb)
    if mag1 * mag2 == 0:
        return 0.0
    v = dot(ab, cb) / (mag1 * mag2)
    v = max(min(v, 1.0), -1.0)
    return math.degrees(math.acos(v))


def angle_between_vectors(v1, v2):
    mag1 = vec_len(v1)
    mag2 = vec_len(v2)
    if mag1 * mag2 == 0:
        return 0.0
    v = dot(v1, v2) / (mag1 * mag2)
    v = max(min(v, 1.0), -1.0)
    return math.degrees(math.acos(v))


def wrist_position(lm):
    """Return wrist dict for JSON."""
    return {"x": lm[0].x, "y": lm[0].y, "z": lm[0].z}


def palm_size(lm):
    """Use wrist -> middle MCP as palm reference length."""
    return dist(lm[0], lm[9])


def finger_direction(lm, tip, pip):
    """Normalized direction vector for a finger (PIP -> tip)."""
    return normalize((lm[tip].x - lm[pip].x, lm[tip].y - lm[pip].y, lm[tip].z - lm[pip].z))


def finger_joint_angles(lm, tip, dip, pip, mcp):
    """Return (pip_angle, dip_angle) in degrees using full 3D vectors."""
    pip_vec_prox = (lm[mcp].x - lm[pip].x, lm[mcp].y - lm[pip].y, lm[mcp].z - lm[pip].z)
    pip_vec_dist = (lm[dip].x - lm[pip].x, lm[dip].y - lm[pip].y, lm[dip].z - lm[pip].z)
    dip_vec_prox = (lm[pip].x - lm[dip].x, lm[pip].y - lm[dip].y, lm[pip].z - lm[dip].z)
    dip_vec_dist = (lm[tip].x - lm[dip].x, lm[tip].y - lm[dip].y, lm[tip].z - lm[dip].z)
    pip_angle = angle_between_vectors(pip_vec_prox, pip_vec_dist)
    dip_angle = angle_between_vectors(dip_vec_prox, dip_vec_dist)
    return pip_angle, dip_angle


def finger_curl_state(pip_angle, dip_angle, strong_thresh=90.0, partial_thresh=120.0):
    """
    Use sum of PIP+DIP angles to derive qualitative curl state and score.
    """
    total = pip_angle + dip_angle
    if total > strong_thresh:
        return "curled", 1.0
    if total > partial_thresh:
        return "partial", 0.5
    return "extended", 0.0


def normalized_distance(value, scale):
    if scale <= 1e-6:
        return 0.0
    return clamp01(value / scale)


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

    # # # x0, y0 = 10, 30 + offset_y
    # # # dy = 20
    # # # pinch_comp = hand_data.pinch_components or {"tip": 0.0, "depth": 0.0, "angle": 0.0}
    # # # info = [
    # # #     f"hand: {hand_data.handedness}",
    # # #     f"gesture: {hand_data.gesture}",
    # # #     f"visible: {hand_data.visible}",
    # # #     f"conf: {hand_data.confidence:.2f}",
    # # #     f"pinch_dist: {hand_data.pinch_distance:.3f}",
    # # #     (
    # # #         f"pinch_strength: {hand_data.pinch_strength:.2f} "
    # # #         f"(conf {hand_data.pinch_confidence:.2f})"
    # # #     ),
    # # #     (
    # # #         "pinch components "
    # # #         f"(tip={pinch_comp.get('tip',0.0):.2f}, "
    # # #         f"depth={pinch_comp.get('depth',0.0):.2f}, "
    # # #         f"angle={pinch_comp.get('angle',0.0):.2f})"
    # # #     ),
    # # #     f"thumb_angle: {hand_data.thumb_angle:.1f}",
    # # #     f"curled: {hand_data.curled_count} | extended: {hand_data.extended_count}",
    # # #     f"wrist: ({hand_data.wrist['x']:.2f},{hand_data.wrist['y']:.2f},{hand_data.wrist['z']:.2f})",
    # # #     f"t: {hand_data.timestamp:.2f}, dt:{hand_data.dt:.3f}",
    # # # ]
    # # # finger_names = ["Index", "Middle", "Ring", "Pinky"]
    # # # for idx, name in enumerate(finger_names):
    # # #     angle = 0.0
    # # #     if idx < len(hand_data.curl_angles):
    # # #         angle = hand_data.curl_angles[idx]
    # # #     score = hand_data.curl_scores[idx] if idx < len(hand_data.curl_scores) else 0.0
    # # #     state = hand_data.curl_states[idx] if idx < len(hand_data.curl_states) else "?"
    # # #     info.append(
    # # #         f"{name[:5]}: angle={angle:05.1f}° state={state:<9} score={score:.2f}"
    # # #     )


def draw_joint_angle_labels(
    frame,
    hand_data,
    buffer: FingerAngleBuffer,
    color=(0, 255, 255),
    font_scale=0.35,
    thickness=1,
):
    """
    Draw bent-angle values next to each joint defined in FINGER_JOINTS.
    Expects a persistent FingerAngleBuffer per-hand for smoothing.
    """
    if (
        frame is None
        or hand_data is None
        or hand_data.raw_landmarks is None
        or buffer is None
    ):
        return

    lm = hand_data.raw_landmarks.landmark
    if not lm:
        return

    h, w, _ = frame.shape
    angles = compute_smoothed_finger_angles(
        lm, buffer, handedness=hand_data.handedness
    )

    for finger_name, joints in FINGER_JOINTS.items():
        finger_angles = angles.get(finger_name, [])
        for joint_idx, (_, target_idx, _) in enumerate(joints):
            if target_idx >= len(lm) or joint_idx >= len(finger_angles):
                continue
            joint = lm[target_idx]
            x = int(joint.x * w)
            y = int(joint.y * h)
            text = f"{finger_angles[joint_idx]:+.0f}"

            (tw, th), baseline = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
            )
            box_pt1 = (x, y - th - baseline - 2)
            box_pt2 = (x + tw + 2, y + baseline + 2)
            cv2.rectangle(frame, box_pt1, box_pt2, (0, 0, 0), -1)
            cv2.putText(
                frame,
                text,
                (x + 1, y + 1),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                color,
                thickness,
                cv2.LINE_AA,
            )
    # # # for i, line in enumerate(info):
    # # #     cv2.putText(
    # # #         frame,
    # # #         line,
    # # #         (x0, y0 + i * dy),
    # # #         cv2.FONT_HERSHEY_SIMPLEX,
    # # #         0.55,
    # # #         (0, 255, 0),
    # # #         1,
    # # #         cv2.LINE_AA,
    # # #     )


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
