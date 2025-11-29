import time
import cv2
import threading
from queue import Queue, Empty
from collections import deque

from HandTracker import HandTracker
from GestureClassifier import GestureClassifier
from GestureServer import GestureServer
from helpers import draw_hand_debug, load_config, ConfigWatcher


# --------------------------------------------------------
# Queue for latest frame only (overwrite when full)
# --------------------------------------------------------
FRAME_QUEUE_MAX = 1


# --------------------------------------------------------
# CAPTURE THREAD
# --------------------------------------------------------
def capture_thread(frame_queue, stop_event, cfg):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[PY] ERROR: Cannot open camera")
        stop_event.set()
        return

    tracker = HandTracker(cfg)

    # FPS calculation
    fps_window = cfg["debug"].get("fps_window", 20)
    fps_times = deque(maxlen=fps_window)
    current_fps = 0.0

    last_time = time.time()

    print("[PY] Capture thread started.")

    while not stop_event.is_set():
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.01)
            continue

        now = time.time()
        dt = now - last_time
        last_time = now

        # Update FPS
        fps_times.append(now)
        if len(fps_times) > 1:
            current_fps = (len(fps_times) - 1) / (fps_times[-1] - fps_times[0])

        # Convert frame → RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands = tracker.process_frame(rgb, now)

        # Assign dt to each hand
        for h in hands:
            h.dt = dt

        # Insert latest sample (frame, hands, timestamp, fps)
        try:
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()  # remove older frame
                except Empty:
                    pass
            frame_queue.put_nowait((frame, hands, now, current_fps))
        except Exception:
            pass

        # -------------------------------
        # Debug drawing
        # -------------------------------
        if cfg["debug"].get("draw_landmarks", True):
            if hands:
                for i, h in enumerate(hands):
                    draw_hand_debug(frame, h, offset_y=i * 180)
            else:
                cv2.putText(
                    frame,
                    "No hands",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 0, 255),
                    2,
                )

        # FPS text overlay
        if cfg["debug"].get("show_fps", True):
            cv2.putText(
                frame,
                f"FPS: {current_fps:.1f}",
                (10, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2,
            )

        cv2.imshow("Gesture Debug", frame)

        # ESC to quit
        if cv2.waitKey(1) & 0xFF == 27:
            stop_event.set()
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[PY] Capture thread exiting.")


# --------------------------------------------------------
# CLASSIFIER THREAD
# --------------------------------------------------------
def classifier_thread(frame_queue, stop_event, cfg):
    classifier = GestureClassifier(cfg)
    server = GestureServer()

    last_time_per_hand = {}  # handedness → timestamp of last classification

    cfg_watcher = ConfigWatcher("config.json")
    cfg = cfg_watcher.get_config()
    classifier = GestureClassifier(cfg)
    server = GestureServer()

    print("[PY] Classifier thread started.")

    while not stop_event.is_set():
        try:
            frame, hands, timestamp, fps = frame_queue.get(timeout=0.1)
        except Empty:
            continue

        new_cfg = cfg_watcher.check_reload()
        if new_cfg != cfg:
            cfg = new_cfg
        classifier.update_config(cfg)

        # Update correct dt per hand
        for h in hands:
            key = h.handedness or "Unknown"
            prev_t = last_time_per_hand.get(key, None)

            if prev_t is not None:
                h.dt = h.timestamp - prev_t

            last_time_per_hand[key] = h.timestamp

            classifier.classify_hands(hands)

        # Send JSON snapshot with FPS
        try:
            server.send_hands(hands, fps=fps)
        except Exception as e:
            print("[PY] ERROR sending to C++:", e)
            stop_event.set()
            break

    print("[PY] Classifier thread exiting.")


# --------------------------------------------------------
# MAIN ENTRY
# --------------------------------------------------------
def main():
    # Load config.json
    cfg = load_config("config.json")
    if not cfg:
        print("[PY] WARNING: no config.json or failed to load.")

    frame_queue = Queue(maxsize=FRAME_QUEUE_MAX)
    stop_event = threading.Event()

    # --------------- start threads ----------------
    cap_thread = threading.Thread(
        target=capture_thread, args=(frame_queue, stop_event, cfg), daemon=True
    )
    class_thread = threading.Thread(
        target=classifier_thread, args=(frame_queue, stop_event, cfg), daemon=True
    )

    cap_thread.start()
    class_thread.start()

    # Keep main thread alive
    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_event.set()

    cap_thread.join(timeout=1.0)
    class_thread.join(timeout=1.0)

    print("[PY] Shutdown complete.")


if __name__ == "__main__":
    main()
