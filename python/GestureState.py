import json


# ==========================================
# 2. PERSISTENT STATE (Memory Management)
# ==========================================
class GestureState:
    """
    Stores persistent data between frames to avoid reallocation.
    Replaces 'HandData' instantiation every frame.
    """

    def __init__(self):
        # Smoothing History: Map[Handedness -> List[Landmarks]]
        self.prev_landmarks = {"Left": None, "Right": None}

        # State Machine: Deduplicate network events
        self.last_gesture = {"Left": "NONE", "Right": "NONE"}
        self.last_sent_time = 0

        # Configuration
        try:
            with open("config.json", "r") as f:
                self.cfg = json.load(f)
        except:
            print("[WARN] Config not found, using defaults")
            self.cfg = {"smoothing": {"alpha": 0.6}, "thresholds": {"pinch_dist": 0.05}}

        # Cache config values for speed
        self.alpha = self.cfg.get("smoothing", {}).get("alpha", 0.6)
        self.pinch_thresh = self.cfg.get("thresholds", {}).get("pinch_dist", 0.05)
