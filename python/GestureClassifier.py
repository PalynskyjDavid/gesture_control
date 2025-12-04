# GestureClassifier.py
import time
from collections import defaultdict, Counter, deque
from HandData import HandData
from helpers import (
    dist,
    angle,
    normalized_distance,
    angle_between_vectors,
    clamp01,
    palm_size as compute_palm_size,
    finger_direction,
)
from HandFeatures import HandFeatureExtractor


class GestureClassifier:
    def __init__(self, cfg=None):
        # default config
        self.cfg = {
            "classifier": {
                "history_len": 4,
                "swipe_speed_thresh": 1.0,
                "zoom_speed_thresh": 0.15,
                "drag_speed_thresh": 0.05,
                "pinch_distance_threshold": 0.08,
                "pinch_thumb_angle_thresh": 160,
            },
            "multi_hand": {
                "enable_two_hand_zoom": True,
                "two_hand_zoom_window": 4,
                "two_hand_zoom_thresh": 0.03,
            },
            "smoothing": {
                "mode": "voting",
                "ema_alpha": 0.4,
                "hysteresis_enter": 0.7,
                "hysteresis_exit": 0.4,
            },
        }
        if cfg:
            self.update_config(cfg)

        self.label_history = defaultdict(list)
        self.wrist_history = defaultdict(list)
        self.pinch_history = defaultdict(list)
        self.feature_extractor = HandFeatureExtractor()

        # EMA maps: handedness -> {label: score}
        self.ema_scores = defaultdict(lambda: defaultdict(float))

        # hysteresis: last label per hand
        self.last_label = {}

        # inter-hand history for two-hand zoom
        self.interhand_history = deque(maxlen=self.two_hand_zoom_window)
        self.pinch_strength_ema = defaultdict(float)
        self.pinch_state = defaultdict(bool)

    def update_config(self, cfg):
        # deep-merge new cfg into self.cfg
        if not cfg:
            return
        # simple merge
        for k, v in cfg.items():
            if isinstance(v, dict):
                self.cfg.setdefault(k, {}).update(v)
            else:
                self.cfg[k] = v

        c = self.cfg.get("classifier", {})
        mh = self.cfg.get("multi_hand", {})
        s = self.cfg.get("smoothing", {})

        self.history_len = c.get("history_len", 4)
        self.swipe_speed_thresh = c.get("swipe_speed_thresh", 1.0)
        self.zoom_speed_thresh = c.get("zoom_speed_thresh", 0.15)
        self.drag_speed_thresh = c.get("drag_speed_thresh", 0.05)
        self.pinch_distance_threshold = c.get("pinch_distance_threshold", 0.08)
        self.pinch_thumb_angle_thresh = c.get("pinch_thumb_angle_thresh", 50)
        self.curl_strong_angle = c.get("curl_strong_angle", 90.0)
        self.curl_partial_angle = c.get("curl_partial_angle", 120.0)
        self.pinch_strength_enter = c.get("pinch_strength_enter", 0.75)
        self.pinch_strength_exit = c.get("pinch_strength_exit", 0.6)
        self.pinch_ema_alpha = c.get("pinch_ema_alpha", 0.5)
        self.pinch_distance_norm = c.get("pinch_distance_norm", 0.6)
        self.pinch_depth_norm = c.get("pinch_depth_norm", 0.4)
        self.pinch_weights = c.get(
            "pinch_weights", {"tip": 0.5, "depth": 0.2, "angle": 0.3}
        )

        self.enable_two_hand_zoom = mh.get("enable_two_hand_zoom", True)
        self.two_hand_zoom_window = mh.get("two_hand_zoom_window", 4)
        self.two_hand_zoom_thresh = mh.get("two_hand_zoom_thresh", 0.03)

        self.smoothing_mode = s.get("mode", "voting")
        self.ema_alpha = s.get("ema_alpha", 0.4)
        self.hysteresis_enter = s.get("hysteresis_enter", 0.7)
        self.hysteresis_exit = s.get("hysteresis_exit", 0.4)

        # ensure interhand history length
        old = list(getattr(self, "interhand_history", []))
        self.interhand_history = deque(old, maxlen=self.two_hand_zoom_window)

        buffer_len = c.get("joint_angle_buffer", 5)
        self.feature_extractor.configure(
            buffer_size=buffer_len,
            strong_thresh=self.curl_strong_angle,
            partial_thresh=self.curl_partial_angle,
        )

    # helper history push
    def _push_hist(self, hist, key, entry):
        h = hist[key]
        h.append(entry)
        if len(h) > self.history_len:
            h.pop(0)

    def _compute_velocity(self, wrist_hist):
        if len(wrist_hist) < 2:
            return 0.0, 0.0
        t0, x0, y0 = wrist_hist[0]
        t1, x1, y1 = wrist_hist[-1]
        dt = t1 - t0
        if dt <= 1e-6: # Q: Does this calculate time between two frames?
            return 0.0, 0.0
        return (x1 - x0) / dt, (y1 - y0) / dt # Q: Should not there be some small treshold and not technical zero as there will always be some small wrist movement or is it then handled on backed?

    def _compute_pinch_velocity(self, pinch_hist):
        if len(pinch_hist) < 2:
            return 0.0
        t0, d0 = pinch_hist[0]
        t1, d1 = pinch_hist[-1]
        dt = t1 - t0
        if dt <= 1e-6:
            return 0.0
        return (d1 - d0) / dt # Q: Similar as above, shoult it not recognize fast/slow pinch movement, maybe with some small treshold under slow movement?

    def _apply_smoothing(self, handed, candidate): # Q: This one simply counts all gestures in history and chooses the most common one, but what does candidate parameter do/mean?
        """
        handed: "Left" or "Right"
        candidate: label string (from current frame)
        returns: (final_label, confidence [0..1])
        """
        if self.smoothing_mode == "voting":
            hist = self.label_history[handed]
            hist.append(candidate)
            if len(hist) > self.history_len:
                hist.pop(0)
            counts = Counter(hist)
            label, votes = counts.most_common(1)[0]
            conf = votes / len(hist) if len(hist) > 0 else 0.0
            return label, conf

        if self.smoothing_mode == "ema": # Q: Does this make newer gestures more important than older ones, does it still after that work like voting algorithm above?
            # add 1.0 to candidate and decay others
            scores = self.ema_scores[handed]
            for k in list(scores.keys()):
                scores[k] = scores[k] * (1.0 - self.ema_alpha)
                if scores[k] < 1e-6:
                    del scores[k]
            scores[candidate] = scores.get(candidate, 0.0) + self.ema_alpha
            # pick top
            label, val = max(scores.items(), key=lambda kv: kv[1])
            # normalize confidence approximate
            total = sum(scores.values()) if scores else 1.0
            return label, (val / total) if total > 0 else 0.0

        if self.smoothing_mode == "hysteresis": # Q: How does this work?
            last = self.last_label.get(handed, None)
            if last is None:
                # initialize
                self.last_label[handed] = candidate # Q: So when programs starts and "buffer" is not full then its filled with candidates?
                return candidate, 1.0
            if candidate == last:
                return last, 1.0
            # if candidate different, require confidence to enter
            # use simple voting on short window for candidate
            hist = self.label_history[handed]
            hist.append(candidate)
            if len(hist) > self.history_len:
                hist.pop(0)
            counts = Counter(hist)
            votes = counts.get(candidate, 0)
            conf = votes / len(hist)
            # enter if conf > enter threshold; exit (revert) if below exit threshold
            if conf >= self.hysteresis_enter:
                self.last_label[handed] = candidate
                return candidate, conf
            # otherwise keep last
            return last, max(conf, self.hysteresis_exit)

        # fallback
        return candidate, 1.0

    def classify_single(self, hand: HandData, hand_index: int = 0):
        # identical feature calc as earlier
        now = hand.timestamp
        lm = hand.landmarks
        if lm is None:
            hand.gesture = "none"
            hand.confidence = 0.0
            return hand

        hand.palm_size = hand.palm_size or compute_palm_size(lm)
        hand.pinch_distance = dist(lm[4], lm[8])
        hand.thumb_angle = angle(lm[4], lm[3], lm[2])

        feature_key = f"{hand.handedness or 'Unknown'}_{hand_index}"
        self.feature_extractor.process_hand(hand, feature_key)

        curls = list(hand.curls or [])
        while len(curls) < 4:
            curls.append(False)
        index_curled, middle_curled, ring_curled, pinky_curled = curls[:4]
        hand.wrist["x"] = lm[0].x
        hand.wrist["y"] = lm[0].y
        hand.wrist["z"] = lm[0].z

        if not any(
            abs(comp) > 1e-6
            for vec in hand.direction_vectors.values()
            for comp in vec
        ):
            finger_map = {
                "thumb": (4, 3),
                "index": (8, 7),
                "middle": (12, 11),
                "ring": (16, 15),
                "pinky": (20, 19),
            }
            for name, (tip, pip) in finger_map.items():
                hand.direction_vectors[name] = finger_direction(lm, tip, pip)

        key = hand.handedness or "Unknown"
        self._push_hist(
            self.wrist_history, key, (hand.timestamp, hand.wrist["x"], hand.wrist["y"])
        )
        self._push_hist(self.pinch_history, key, (hand.timestamp, hand.pinch_distance))

        vx, vy = self._compute_velocity(self.wrist_history[key])
        pinch_v = self._compute_pinch_velocity(self.pinch_history[key])

        finger_states = hand.finger_states_map or {}
        thumb_state = finger_states.get("thumb", "extended")
        others_curled = all(
            (finger_states.get(name, "extended") != "extended")
            for name in ("index", "middle", "ring", "pinky")
        )

        static = "unknown"
        if thumb_state == "extended" and others_curled:
            static = "thumbs_up"
        elif hand.curled_count >= 3:
            static = "fist"
        elif hand.extended_count >= 3:
            static = "open_palm"
        elif (not index_curled) and middle_curled and ring_curled and pinky_curled:
            static = "point_index"

        dynamic = None
        if static in ("open_palm", "point_index"):
            if abs(vx) > abs(vy) and abs(vx) > self.swipe_speed_thresh:
                dynamic = "swipe_right" if vx > 0 else "swipe_left"
            elif abs(vy) > abs(vx) and abs(vy) > self.swipe_speed_thresh:
                dynamic = "swipe_down" if vy > 0 else "swipe_up"

        palm_norm = max(hand.palm_size, 1e-6)
        tip_score = 1.0 - normalized_distance(
            hand.pinch_distance, palm_norm * max(self.pinch_distance_norm, 1e-6)
        )
        depth_delta = abs(lm[4].z - lm[8].z)
        depth_score = 1.0 - normalized_distance(
            depth_delta, palm_norm * max(self.pinch_depth_norm, 1e-6)
        )
        thumb_dir = hand.direction_vectors.get("thumb", (0.0, 0.0, 0.0))
        index_dir = hand.direction_vectors.get("index", (0.0, 0.0, 0.0))
        angle_val = angle_between_vectors(thumb_dir, index_dir)
        angle_score = 1.0 - clamp01(angle_val / 180.0)
        weights = self.pinch_weights
        total_w = max(
            weights.get("tip", 0.5) + weights.get("depth", 0.2) + weights.get("angle", 0.3),
            1e-6,
        )
        pinch_strength = (
            weights.get("tip", 0.5) * tip_score
            + weights.get("depth", 0.2) * depth_score
            + weights.get("angle", 0.3) * angle_score
        ) / total_w
        hand.pinch_components = {
            "tip": tip_score,
            "depth": depth_score,
            "angle": angle_score,
        }
        hand.pinch_strength = clamp01(pinch_strength)

        prev_ema = self.pinch_strength_ema[key]
        ema = (1.0 - self.pinch_ema_alpha) * prev_ema + self.pinch_ema_alpha * hand.pinch_strength
        self.pinch_strength_ema[key] = ema
        hand.pinch_confidence = ema

        pinch_active = self.pinch_state.get(key, False)
        if pinch_active:
            if ema < self.pinch_strength_exit:
                pinch_active = False
        else:
            if ema > self.pinch_strength_enter:
                pinch_active = True
        self.pinch_state[key] = pinch_active

        pinch_like = pinch_active
        zoom_label = None
        if pinch_like and abs(pinch_v) > self.zoom_speed_thresh:
            zoom_label = "zoom_in" if pinch_v > 0 else "zoom_out"

        final = static
        if zoom_label:
            final = zoom_label
        elif dynamic:
            final = dynamic
        elif static == "fist":
            if abs(vx) > self.drag_speed_thresh or abs(vy) > self.drag_speed_thresh:
                final = "grab"
            else:
                final = "fist"

        # keep history for voting/hysteresis, etc
        hist = self.label_history[key]
        hist.append(final)
        if len(hist) > self.history_len:
            hist.pop(0)

        # smoothing choice
        label, conf = self._apply_smoothing(key, final)
        hand.gesture = label
        hand.confidence = conf
        return hand

    def classify_hands(self, hands):
        # single-hand compute
        for idx, h in enumerate(hands):
            self.classify_single(h, idx)

        # two-hand zoom logic
        if self.enable_two_hand_zoom and len(hands) >= 2:
            # choose pair, prefer Left+Right
            by_hand = {h.handedness: h for h in hands}
            if "Left" in by_hand and "Right" in by_hand:
                h0 = by_hand["Left"]
                h1 = by_hand["Right"]
            else:
                h0 = hands[0]
                h1 = hands[1]

            d = (
                (h0.wrist["x"] - h1.wrist["x"]) ** 2
                + (h0.wrist["y"] - h1.wrist["y"]) ** 2
            ) ** 0.5
            t = max(h0.timestamp, h1.timestamp) # Q: This variable "t" is not used anywhere?
            self.interhand_history.append((t, d))

            if len(self.interhand_history) >= 2:
                t0, d0 = self.interhand_history[0]
                t1, d1 = self.interhand_history[-1]
                dt = t1 - t0 if t1 - t0 > 1e-6 else 1e-6
                dv = (d1 - d0) / dt
                if abs(dv) > self.two_hand_zoom_thresh:
                    lbl = "zoom_in" if dv > 0 else "zoom_out"
                    for hh in hands:
                        hh.gesture = lbl
                        hh.confidence = 1.0
                    return hands

        return hands
    # Q: This logic seems to recognize only single hand gestures except two-hand zoom, should there be some other multi-hand gestures recognized? Also how to organize logic frstly calculate all variables like bent fingers etc. and then check for two handed gestures and then single handed ones?
