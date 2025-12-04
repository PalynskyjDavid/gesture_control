import cv2
import mediapipe as mp
from GestureState import GestureState
from Network import NetworkBridge
from FeatureExtractor import vec_dist, compute_angle

# ==========================================
# 4. PROCESSING CORE
# ==========================================
class GestureProcessor:
    def __init__(self):
        self.mp_hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.state = GestureState()
        self.network = NetworkBridge()

    def smooth_landmarks(self, raw_landmarks, handedness):
        """
        Exponential Moving Average (EMA) filter.
        Mutates state, does not create new objects if possible.
        """
        prev = self.state.prev_landmarks.get(handedness)

        if prev is None:
            # First frame, just store raw
            self.state.prev_landmarks[handedness] = raw_landmarks
            return raw_landmarks

        alpha = self.state.alpha
        smoothed = []

        # We must iterate because MP landmarks are not simple arrays
        for i in range(len(raw_landmarks.landmark)):
            curr_pt = raw_landmarks.landmark[i]
            prev_pt = prev.landmark[i]

            # Math: S_t = alpha * Y_t + (1 - alpha) * S_{t-1}
            # Note: We can't mutate MediaPipe objects directly easily,
            # so we return a lightweight object or wrapper.
            # For simplicity here, we use a simple dict-like structure or just raw values.
            # To keep it compatible with 'raw_landmarks' structure for drawing,
            # we often just write back to a persistent buffer.

            # Optimization: Just smooth the specific points we need?
            # No, smooth all for visual consistency if drawing.

            # Hack for performance: We modify the 'raw_landmarks' object in place
            # effectively treating it as our output buffer for this frame.

            new_x = alpha * curr_pt.x + (1 - alpha) * prev_pt.x
            new_y = alpha * curr_pt.y + (1 - alpha) * prev_pt.y
            new_z = alpha * curr_pt.z + (1 - alpha) * prev_pt.z

            # Warning: This mutation is valid in Python but modifies the MP result
            curr_pt.x = new_x
            curr_pt.y = new_y
            curr_pt.z = new_z

        self.state.prev_landmarks[handedness] = raw_landmarks
        return raw_landmarks

    def classify_gesture(self, landmarks):
        """
        Simple Decision Tree Classifier.
        Returns: String (Gesture Name)
        """
        lm = landmarks.landmark

        # 1. Pinch Check (Index Tip -> Thumb Tip)
        pinch_dist = vec_dist(lm[8], lm[4])
        if pinch_dist < self.state.pinch_thresh:
            return "PINCH"

        # 2. Finger States (Extended vs Curled)
        # Using angle at PIP joint is robust.
        # Index: 0 -> 5 -> 6 -> 8. Angle at 6 (PIP) or 5 (MCP).
        # Simple heuristic: Tip Y < PIP Y (if hand is upright).

        # Robust method: Angle
        # Thumb: 2-3-4
        # Index: 5-6-7-8 (Check angle at 6)
        # Middle: 9-10-11-12 (Check angle at 10)
        # Ring: 13-14-15-16 (Check angle at 14)
        # Pinky: 17-18-19-20 (Check angle at 18)

        angle_index = compute_angle(lm[5], lm[6], lm[7])
        angle_middle = compute_angle(lm[9], lm[10], lm[11])
        angle_ring = compute_angle(lm[13], lm[14], lm[15])
        angle_pinky = compute_angle(lm[17], lm[18], lm[19])

        # Threshold: 160+ is straight, < 100 is curled
        is_index_open = angle_index > 150
        is_middle_open = angle_middle > 150
        is_ring_open = angle_ring > 150
        is_pinky_open = angle_pinky > 150

        open_count = sum([is_index_open, is_middle_open, is_ring_open, is_pinky_open])

        if open_count == 4:
            return "OPEN_PALM"
        if open_count == 0:
            return "FIST"
        if is_index_open and not is_middle_open:
            return "POINT"
        if is_index_open and is_middle_open and not is_ring_open:
            return "PEACE"

        return "UNKNOWN"

    def run(self):
        cap = cv2.VideoCapture(0)
        # Set camera for lower latency (MJPG)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("[SYS] Loop started.")

        mp_draw = mp.solutions.drawing_utils

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                continue

            # 1. Input Layer
            # Flip for mirror view, convert to RGB
            frame = cv2.flip(frame, 1)
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 2. Detector Layer
            # This is the heavy lifting
            results = self.mp_hands.process(img_rgb)

            current_frame_data = {"hands": []}

            if results.multi_hand_landmarks:
                for idx, landmarks in enumerate(results.multi_hand_landmarks):
                    # Get Handedness ("Left" or "Right")
                    handedness = results.multi_handedness[idx].classification[0].label

                    # 3. Smoothing Layer
                    smoothed_lm = self.smooth_landmarks(landmarks, handedness)

                    # 4. Classifier Layer
                    gesture = self.classify_gesture(smoothed_lm)

                    # 5. State Machine Layer (Deduping)
                    # Only add to payload if Changed or is specific streamable gesture
                    prev_gesture = self.state.last_gesture.get(handedness)

                    # Logic: We might want to send continuous updates for "pinch" (for dragging)
                    # but only event updates for "fist" (click).
                    # For now, we send everything, but we flag it.

                    hand_info = {
                        "handedness": handedness,
                        "visible": True,
                        "gesture": gesture,
                        "confidence": 1.0,  # Placeholder
                        "wrist": {
                            "x": landmarks.landmark[0].x,
                            "y": landmarks.landmark[0].y,
                        },
                        # Add pinch data for dragging logic in C++/UE5
                        "pinch_distance": vec_dist(
                            landmarks.landmark[8], landmarks.landmark[4]
                        ),
                    }
                    current_frame_data["hands"].append(hand_info)

                    # Visual Debug
                    mp_draw.draw_landmarks(
                        frame, smoothed_lm, mp.solutions.hands.HAND_CONNECTIONS
                    )
                    cv2.putText(
                        frame,
                        f"{handedness}: {gesture}",
                        (10, 50 + idx * 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2,
                    )

                    self.state.last_gesture[handedness] = gesture

            # 6. Network Output Layer
            # Update network check
            self.network.update()

            # Send data if we have hands detected
            if current_frame_data["hands"]:
                self.network.send_event(current_frame_data)

            # 7. Render
            cv2.imshow("Gesture Pipeline", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                break

        cap.release()
        cv2.destroyAllWindows()
