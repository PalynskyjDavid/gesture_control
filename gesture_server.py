import cv2
import mediapipe as mp
import zmq
import time
import math

mp_hands = mp.solutions.hands.Hands(
    model_complexity=0,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5555")

cap = cv2.VideoCapture(0)

def dist(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

while True:
    ok, frame = cap.read()
    if not ok:
        continue

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = mp_hands.process(frame_rgb)

    gesture = None

    if result.multi_hand_landmarks:
        hand = result.multi_hand_landmarks[0].landmark

        thumb = hand[4]
        index = hand[8]
        d = dist(thumb, index)

        # Pinch detection
        if d < 0.05:
            gesture = "pinch"

        # Fist detection (sample heuristic)
        elif hand[8].y > hand[6].y and hand[12].y > hand[10].y:
            gesture = "fist"

        # Open palm
        else:
            gesture = "open_palm"

    if gesture:
        socket.send_string(gesture)

    cv2.imshow("MediaPipe Hands", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
socket.close()
context.term()
