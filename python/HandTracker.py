import time
import mediapipe as mp
from HandData import HandData
from helpers import palm_size, wrist_position, finger_direction


class HandTracker:
    def __init__(
        self,
        cfg,
    ):
        self.mp_drawing = mp.solutions.drawing_utils
        self.cfg = cfg
        self.debug_cfg = cfg.get("debug", {})
        tcfg = cfg.get("tracker", {})

        self.mp_hands = mp.solutions.hands.Hands(
            model_complexity=tcfg.get("model_complexity", 1),
            min_detection_confidence=tcfg.get("min_detection_confidence", 0.5),
            min_tracking_confidence=tcfg.get("min_tracking_confidence", 0.5),
            max_num_hands=tcfg.get("max_num_hands", 2),
        )

    def process_frame(self, frame_rgb, timestamp):
        """
        Process an RGB frame (expects BGR->RGB already done by caller or pass BGR and change conversion).
        Returns list of HandData instances with raw landmarks + handedness set.
        timestamp: absolute time (seconds) for this frame.
        """
        # MediaPipe expects RGB in uint8
        result = self.mp_hands.process(frame_rgb)
        hands = []

        if not result.multi_hand_landmarks:
            return hands

        for lm, handed in zip(result.multi_hand_landmarks, result.multi_handedness):
            h = HandData()
            h.raw_landmarks = lm
            h.landmarks = lm.landmark
            h.handedness = handed.classification[0].label
            h.visible = True
            h.timestamp = timestamp
            h.palm_size = palm_size(h.landmarks)
            h.wrist = wrist_position(h.landmarks)

            finger_map = {
                "thumb": (4, 3),
                "index": (8, 7),
                "middle": (12, 11),
                "ring": (16, 15),
                "pinky": (20, 19),
            }
            for name, (tip, pip) in finger_map.items():
                h.direction_vectors[name] = finger_direction(h.landmarks, tip, pip)
            # dt is set by classifier thread (if we want previous timestamp difference we can compute there)
            hands.append(h)

        return hands
