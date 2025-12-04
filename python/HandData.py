class HandData:
    """
    Simple container for per-hand data that flows between modules.
    """

    def __init__(self):
        # raw mediapipe landmark object (for drawing)
        self.raw_landmarks = None

        # list of normalized landmarks (landmark objects)
        self.landmarks = None

        # "Left" / "Right"
        self.handedness = "Unknown"

        # boolean flag
        self.visible = False

        # timing
        self.timestamp = 0.0  # absolute time (seconds)
        self.dt = 0.0  # time since previous classified frame (seconds)

        # features computed per frame
        self.pinch_distance = 0.0
        self.thumb_angle = 0.0
        self.curls = [False, False, False, False]  # index..pinky
        self.curl_scores = [0.0, 0.0, 0.0, 0.0]
        self.curl_states = ["extended", "extended", "extended", "extended"]
        self.curl_angles = [0.0, 0.0, 0.0, 0.0]
        self.curled_count = 0
        self.extended_count = 0
        self.joint_angles = {}
        self.finger_bends = {}
        self.finger_states_map = {}
        self.finger_scores_map = {}
        self.palm_size = 0.0
        self.direction_vectors = {
            "thumb": (0.0, 0.0, 0.0),
            "index": (0.0, 0.0, 0.0),
            "middle": (0.0, 0.0, 0.0),
            "ring": (0.0, 0.0, 0.0),
            "pinky": (0.0, 0.0, 0.0),
        }
        self.pinch_strength = 0.0
        self.pinch_confidence = 0.0
        self.pinch_components = {"tip": 0.0, "depth": 0.0, "angle": 0.0}

        # wrist position normalized 0..1
        self.wrist = {"x": 0.0, "y": 0.0, "z": 0.0}

        # classification result
        self.gesture = "none"
        self.confidence = 0.0

    def to_dict(self):
        """Serialize to JSON-friendly dict."""
        return {
            "handedness": self.handedness,
            "visible": self.visible,
            "gesture": self.gesture,
            "confidence": self.confidence,
            "pinch_distance": self.pinch_distance,
            "pinch_strength": self.pinch_strength,
            "pinch_confidence": self.pinch_confidence,
            "pinch_components": self.pinch_components,
            "thumb_angle": self.thumb_angle,
            "curls": self.curls,
            "curl_scores": self.curl_scores,
            "curl_states": self.curl_states,
            "curl_angles": self.curl_angles,
            "curled_count": self.curled_count,
            "extended_count": self.extended_count,
            "joint_angles": self.joint_angles,
            "finger_bends": self.finger_bends,
            "finger_states_map": self.finger_states_map,
            "finger_scores_map": self.finger_scores_map,
            "palm_size": self.palm_size,
            "direction_vectors": {
                name: list(vec) for name, vec in self.direction_vectors.items()
            },
            "wrist": self.wrist,
            "timestamp": self.timestamp,
            "dt": self.dt,
        }
