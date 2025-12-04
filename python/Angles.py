import math
from collections import defaultdict, deque
from typing import Dict, Iterable, List, MutableMapping, Sequence, Tuple, Union

# Each tuple describes (previous, joint, next) landmark indices for a finger joint.
FINGER_JOINTS: Dict[str, Tuple[Tuple[int, int, int], ...]] = {
    "thumb": ((1, 2, 3), (2, 3, 4)),
    "index": ((0, 5, 6), (5, 6, 7), (6, 7, 8)),
    "middle": ((0, 9, 10), (9, 10, 11), (10, 11, 12)),
    "ring": ((0, 13, 14), (13, 14, 15), (14, 15, 16)),
    "pinky": ((0, 17, 18), (17, 18, 19), (18, 19, 20)),
}

Point = Tuple[float, float, float]
LandmarkLike = Union[Sequence[float], MutableMapping[str, float]]


def _extract_point(entry: Union[LandmarkLike, object]) -> Point:
    if hasattr(entry, "x") and hasattr(entry, "y") and hasattr(entry, "z"):
        return (float(entry.x), float(entry.y), float(entry.z))
    if isinstance(entry, dict):
        return (float(entry.get("x", 0.0)), float(entry.get("y", 0.0)), float(entry.get("z", 0.0)))
    if isinstance(entry, (list, tuple)) and len(entry) >= 3:
        return (float(entry[0]), float(entry[1]), float(entry[2]))
    raise ValueError("Unsupported landmark format; expected object with x,y,z or sequence of 3 values.")


def _vec(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Point, b: Point) -> Point:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(v: Point) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _normalize(v: Point) -> Point:
    l = _length(v)
    if l <= 1e-6:
        return (0.0, 0.0, 0.0)
    return (v[0] / l, v[1] / l, v[2] / l)


def _signed_angle_for_triplet(points: Sequence[object], triplet: Tuple[int, int, int], palm_normal: Point) -> float:
    a_idx, b_idx, c_idx = triplet
    try:
        a = _extract_point(points[a_idx])
        b = _extract_point(points[b_idx])
        c = _extract_point(points[c_idx])
    except (IndexError, ValueError):
        return 0.0

    v1 = _vec(a, b)
    v2 = _vec(c, b)
    len1 = _length(v1)
    len2 = _length(v2)
    if len1 <= 1e-6 or len2 <= 1e-6:
        return 0.0

    cosine = _dot(v1, v2) / (len1 * len2)
    cosine = max(min(cosine, 1.0), -1.0)
    angle = math.degrees(math.acos(cosine))

    cross_dir = _cross(v1, v2)
    sign = 1.0
    if _length(cross_dir) > 1e-6 and _length(palm_normal) > 1e-6:
        orientation = _dot(_normalize(cross_dir), palm_normal)
        sign = 1.0 if orientation >= 0.0 else -1.0
    return angle * sign


def compute_palm_normal(landmarks: Sequence[object]) -> Point:
    if len(landmarks) < 18:
        return (0.0, 0.0, 0.0)
    wrist = _extract_point(landmarks[0])
    index_mcp = _extract_point(landmarks[5])
    pinky_mcp = _extract_point(landmarks[17])
    v1 = _vec(index_mcp, wrist)
    v2 = _vec(pinky_mcp, wrist)
    normal = _normalize(_cross(v1, v2))

    # Ensure the normal points opposite to the palm (toward the back of the hand) so that
    # curling towards the palm yields positive values for both hands.
    middle_mcp = _extract_point(landmarks[9])
    wrist_to_middle = _vec(middle_mcp, wrist)
    if _dot(normal, wrist_to_middle) > 0:
        normal = (-normal[0], -normal[1], -normal[2])
    return normal


def compute_finger_angles(
    landmarks: Sequence[object],
    finger_definitions: Dict[str, Tuple[Tuple[int, int, int], ...]] = None,
    handedness: str = None,
) -> Dict[str, List[float]]:
    if not landmarks:
        return {}

    fingers = finger_definitions or FINGER_JOINTS
    palm_normal = compute_palm_normal(landmarks)

    # Flip normal for mirrored coordinate adjustments.
    if handedness and handedness.lower() == "left":
        palm_normal = (-palm_normal[0], -palm_normal[1], -palm_normal[2])

    result: Dict[str, List[float]] = {}
    for finger, joints in fingers.items():
        values: List[float] = []
        for triplet in joints:
            values.append(_signed_angle_for_triplet(landmarks, triplet, palm_normal))
        result[finger] = values
    return result


class FingerAngleBuffer:
    """
    Maintains a short history of joint angles to reduce jitter.
    Call update() per frame to obtain a smoothed angle.
    """

    def __init__(self, size: int = 5):
        self.size = max(1, int(size))
        self._buffer: Dict[Tuple[str, int], deque] = defaultdict(lambda: deque(maxlen=self.size))

    def reset(self) -> None:
        self._buffer.clear()

    def update(self, finger_name: str, joint_index: int, value: float) -> float:
        key = (finger_name, joint_index)
        dq = self._buffer[key]
        dq.append(value)
        return sum(dq) / len(dq)

    def smooth(self, raw_angles: Dict[str, Iterable[float]]) -> Dict[str, List[float]]:
        smoothed: Dict[str, List[float]] = {}
        for finger, angles in raw_angles.items():
            smoothed[finger] = []
            for idx, val in enumerate(angles):
                smoothed[finger].append(self.update(finger, idx, float(val)))
        return smoothed


def compute_smoothed_finger_angles(
    landmarks: Sequence[object],
    buffer: FingerAngleBuffer,
    finger_definitions: Dict[str, Tuple[Tuple[int, int, int], ...]] = None,
    handedness: str = None,
) -> Dict[str, List[float]]:
    raw = compute_finger_angles(landmarks, finger_definitions=finger_definitions, handedness=handedness)
    return buffer.smooth(raw)
