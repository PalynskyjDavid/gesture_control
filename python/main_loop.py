import time
import cv2
import threading
from queue import Queue, Empty
from collections import deque, defaultdict

from HandTracker import HandTracker
from GestureClassifier import GestureClassifier
from GestureServer import GestureServer
from helpers import (
    draw_hand_debug,
    draw_joint_angle_labels,
    load_config,
    ConfigWatcher,
)
from Boundaries import (
    build_and_draw_tilted_plane,
    # point_above_plane,
    # draw_debug_reference_plane,
    annotate_fingertip_plane_status,
)
from Angles import FingerAngleBuffer, compute_smoothed_finger_angles


# --------------------------------------------------------
# Queue for latest frame only (overwrite when full)
# --------------------------------------------------------
FRAME_QUEUE_MAX = 1
ANGLE_BUFFERS = defaultdict(lambda: FingerAngleBuffer(size=5))


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
    debug_cfg = cfg.get("debug", {})

    # FPS calculation
    fps_window = debug_cfg.get("fps_window", 20)
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

    cap.release()
    print("[PY] Capture thread exiting.")


# --------------------------------------------------------
# CLASSIFIER THREAD
# --------------------------------------------------------
def classifier_thread(frame_queue, stop_event, cfg):
    cfg_watcher = ConfigWatcher("config.json")
    current_cfg = cfg_watcher.get_config()
    if not current_cfg:
        current_cfg = cfg or {}

    classifier = GestureClassifier(current_cfg)
    server = GestureServer()

    last_time_per_hand = {}  # handedness → timestamp of last classification
    debug_window = "Gesture Debug"
    camera_cfg = current_cfg.get("camera", {})
    frame_width = camera_cfg.get("frame_width", 1920)
    frame_height = camera_cfg.get("frame_height", 1080)
    cv2.namedWindow(debug_window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(debug_window, frame_width, frame_height)

    print("[PY] Classifier thread started.")

    buffer = FingerAngleBuffer(size=5)

    while not stop_event.is_set():
        try:
            frame, hands, timestamp, fps = frame_queue.get(timeout=0.1)
        except Empty:
            continue

        new_cfg = cfg_watcher.check_reload()
        if new_cfg and new_cfg != current_cfg:
            current_cfg = new_cfg
        classifier.update_config(current_cfg)

        # Update correct dt per hand
        for h in hands:
            key = h.handedness or "Unknown"
            prev_t = last_time_per_hand.get(key, None)

            if prev_t is not None:
                h.dt = h.timestamp - prev_t

            last_time_per_hand[key] = h.timestamp

        classifier.classify_hands(hands)

        # -------------------------------
        # Debug drawing happens after classification so values are populated.
        # -------------------------------
        debug_cfg = current_cfg.get("debug", {})
        if debug_cfg.get("draw_landmarks", True):
            if hands:
                for i, h in enumerate(hands):
                    draw_hand_debug(frame, h, offset_y=i * 180)

                    smoothed = compute_smoothed_finger_angles(
                        h.landmarks, buffer, handedness=h.handedness
                    )

                    buffer_key = f"{h.handedness or 'Unknown'}_{i}"
                    draw_joint_angle_labels(
                        frame,
                        h,
                        ANGLE_BUFFERS[buffer_key],
                    )
                    # 1. Build the rotated plane (e.g., -20 degrees tilts it "forward" to cut the fingers)
                    # plane_pt, plane_normal = build_and_draw_tilted_plane(
                    #     frame, h, tilt_angle_deg=-20
                    # )

                    # 2. Check if fingers are Open or Closed relative to that plane
                    # annotate_fingertip_plane_status(frame, h, plane_pt, plane_normal)

                    # # # plane_point, plane_normal = draw_debug_reference_plane(frame, hand_data=h)
                    # # # annotate_fingertip_plane_status(frame, h, plane_point, plane_normal)

                    # plane_point, plane_normal = build_and_draw_tilted_plane(
                    #     frame, h, indexes=[0, 9, 5], tiltPointIndex=0, tiltAngleDeg=20
                    # )
                    # Q = h.raw_landmarks.landmark[12]  # fingertip for example
                    # state = point_above_plane(Q, plane_point, plane_normal)

                    # if state == +1:
                    #     print("Point is ABOVE the plane")
                    # elif state == -1:
                    #     print("Point is BELOW the plane")
                    # else:
                    #     print("Point is ON the plane")

            # # # else:
            # # #     cv2.putText(
            # # #         frame,
            # # #         "No hands",
            # # #         (10, 30),
            # # #         cv2.FONT_HERSHEY_SIMPLEX,
            # # #         1.0,
            # # #         (0, 0, 255),
            # # #         2,
            # # #     )

        # # # if debug_cfg.get("show_fps", True):
        # # #     cv2.putText(
        # # #         frame,
        # # #         f"FPS: {fps:.1f}" if fps is not None else "FPS: n/a",
        # # #         (10, frame.shape[0] - 20),
        # # #         cv2.FONT_HERSHEY_SIMPLEX,
        # # #         0.7,
        # # #         (255, 255, 0),
        # # #         2,
        # # #     )

        cv2.imshow(debug_window, frame)
        if cv2.waitKey(1) & 0xFF == 27:
            stop_event.set()
            break

        # Send JSON snapshot with FPS
        try:
            server.send_hands(hands, fps=fps)
        except Exception as e:
            print("[PY] ERROR sending to C++:", e)
            stop_event.set()
            break

    cv2.destroyAllWindows()
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
