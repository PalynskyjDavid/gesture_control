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
        self.curled_count = 0
        self.extended_count = 0

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
            "thumb_angle": self.thumb_angle,
            "curls": self.curls,
            "curled_count": self.curled_count,
            "extended_count": self.extended_count,
            "wrist": self.wrist,
            "timestamp": self.timestamp,
            "dt": self.dt,
        }
