from typing import Dict, List, Tuple

from Angles import FINGER_JOINTS, FingerAngleBuffer, compute_smoothed_finger_angles


class HandFeatureExtractor:
    """
    Computes per-hand joint angles and derived curl states with smoothing.
    Stores results back on the provided HandData objects.
    """

    def __init__(self, buffer_size: int = 5, strong_thresh: float = 90.0, partial_thresh: float = 120.0):
        self.buffer_size = max(5, int(buffer_size))
        self.strong_thresh = strong_thresh
        self.partial_thresh = partial_thresh
        self._buffers: Dict[str, FingerAngleBuffer] = {}

    def configure(self, buffer_size: int = None, strong_thresh: float = None, partial_thresh: float = None) -> None:
        if buffer_size is not None and buffer_size != self.buffer_size:
            self.buffer_size = max(1, int(buffer_size))
            self._buffers.clear()
        if strong_thresh is not None:
            self.strong_thresh = strong_thresh
        if partial_thresh is not None:
            self.partial_thresh = partial_thresh

    def process(self, hands, key_prefix: str = "") -> None:
        for idx, hand in enumerate(hands):
            key = f"{key_prefix}{hand.handedness or 'Unknown'}_{idx}"
            self._process_single(hand, key)

    def process_hand(self, hand, key: str) -> None:
        self._process_single(hand, key)

    def _process_single(self, hand, key: str) -> None:
        if hand is None or hand.landmarks is None:
            return
        buffer = self._get_buffer(key)
        joint_angles = compute_smoothed_finger_angles(
            hand.landmarks, buffer, handedness=hand.handedness
        )
        hand.joint_angles = joint_angles

        bend_summary: Dict[str, Dict[str, float]] = {}
        finger_states: Dict[str, str] = {}
        finger_scores: Dict[str, float] = {}
        curl_bools: List[bool] = []
        curl_states: List[str] = []
        curl_scores: List[float] = []
        curl_angles: List[float] = []

        for finger_name, joints in FINGER_JOINTS.items():
            values = list(joint_angles.get(finger_name, []))
            avg = sum(values) / len(values) if values else 0.0
            max_bend = max(values) if values else 0.0
            min_bend = min(values) if values else 0.0
            latest = values[-1] if values else 0.0
            bend_summary[finger_name] = {
                "avg": avg,
                "max": max_bend,
                "min": min_bend,
                "latest": latest,
            }
            state, score = self._classify_bend(max_bend)
            finger_states[finger_name] = state
            finger_scores[finger_name] = score

        index_order = ["index", "middle", "ring", "pinky"]
        for name in index_order:
            state = finger_states.get(name, "extended")
            score = finger_scores.get(name, 0.0)
            max_bend = bend_summary.get(name, {}).get("max", 0.0)
            curl_bools.append(state != "extended")
            curl_states.append(state)
            curl_scores.append(score)
            curl_angles.append(max_bend)

        hand.finger_bends = bend_summary
        hand.finger_states_map = finger_states
        hand.finger_scores_map = finger_scores

        hand.curls = curl_bools
        hand.curl_states = curl_states
        hand.curl_scores = curl_scores
        hand.curl_angles = curl_angles
        hand.curled_count = sum(1 for v in curl_bools if v)
        hand.extended_count = len(curl_bools) - hand.curled_count

    def _get_buffer(self, key: str) -> FingerAngleBuffer:
        buf = self._buffers.get(key)
        if buf is None or buf.size != self.buffer_size:
            buf = FingerAngleBuffer(size=self.buffer_size)
            self._buffers[key] = buf
        return buf

    def _classify_bend(self, value: float) -> Tuple[str, float]:
        high = max(self.strong_thresh, self.partial_thresh)
        low = min(self.strong_thresh, self.partial_thresh)
        if value >= high:
            return "curled", 1.0
        if value >= low:
            return "partial", 0.5
        return "extended", 0.0
