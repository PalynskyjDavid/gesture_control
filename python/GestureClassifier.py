# GestureClassifier.py
import time
from collections import defaultdict, Counter, deque
from HandData import HandData
from helpers import dist, angle, is_curled


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
                "pinch_thumb_angle_thresh": 50,
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

        # EMA maps: handedness -> {label: score}
        self.ema_scores = defaultdict(lambda: defaultdict(float))

        # hysteresis: last label per hand
        self.last_label = {}

        # inter-hand history for two-hand zoom
        self.interhand_history = deque(maxlen=self.two_hand_zoom_window)

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

        self.enable_two_hand_zoom = mh.get("enable_two_hand_zoom", True)
        self.two_hand_zoom_window = mh.get("two_hand_zoom_window", 4)
        self.two_hand_zoom_thresh = mh.get("two_hand_zoom_thresh", 0.03)

        self.smoothing_mode = s.get("mode", "voting")
        self.ema_alpha = s.get("ema_alpha", 0.4)
        self.hysteresis_enter = s.get("hysteresis_enter", 0.7)
        self.hysteresis_exit = s.get("hysteresis_exit", 0.4)

        # ensure interhand history length
        old = list(self.interhand_history)
        self.interhand_history = deque(old, maxlen=self.two_hand_zoom_window)

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
        if dt <= 1e-6:
            return 0.0, 0.0
        return (x1 - x0) / dt, (y1 - y0) / dt

    def _compute_pinch_velocity(self, pinch_hist):
        if len(pinch_hist) < 2:
            return 0.0
        t0, d0 = pinch_hist[0]
        t1, d1 = pinch_hist[-1]
        dt = t1 - t0
        if dt <= 1e-6:
            return 0.0
        return (d1 - d0) / dt

    def _apply_smoothing(self, handed, candidate):
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

        if self.smoothing_mode == "ema":
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

        if self.smoothing_mode == "hysteresis":
            last = self.last_label.get(handed, None)
            if last is None:
                # initialize
                self.last_label[handed] = candidate
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

    def classify_single(self, hand: HandData):
        # identical feature calc as earlier
        now = hand.timestamp
        lm = hand.landmarks
        if lm is None:
            hand.gesture = "none"
            hand.confidence = 0.0
            return hand

        hand.pinch_distance = dist(lm[4], lm[8])
        hand.thumb_angle = angle(lm[4], lm[3], lm[2])

        index_curled = is_curled(lm, 8, 6, 5)
        middle_curled = is_curled(lm, 12, 10, 9)
        ring_curled = is_curled(lm, 16, 14, 13)
        pinky_curled = is_curled(lm, 20, 18, 17)
        curls = [index_curled, middle_curled, ring_curled, pinky_curled]
        hand.curls = curls
        hand.curled_count = sum(curls)
        hand.extended_count = 4 - hand.curled_count
        hand.wrist["x"] = lm[0].x
        hand.wrist["y"] = lm[0].y
        hand.wrist["z"] = lm[0].z

        key = hand.handedness or "Unknown"
        self._push_hist(
            self.wrist_history, key, (hand.timestamp, hand.wrist["x"], hand.wrist["y"])
        )
        self._push_hist(self.pinch_history, key, (hand.timestamp, hand.pinch_distance))

        vx, vy = self._compute_velocity(self.wrist_history[key])
        pinch_v = self._compute_pinch_velocity(self.pinch_history[key])

        static = "unknown"
        if hand.curled_count >= 3:
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

        pinch_like = (
            hand.pinch_distance < self.pinch_distance_threshold
            and hand.thumb_angle < self.pinch_thumb_angle_thresh
        )
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
        for h in hands:
            self.classify_single(h)

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
            t = max(h0.timestamp, h1.timestamp)
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
