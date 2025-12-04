Thread-Safe Singleton with "atomic updates"
One Class one file - merge them somehow, for example in helpers.py


Camera / Tracking
  └─ HandTracker (frames -> HandData raw landmarks)
       └─ HandData (core data object: raw landmarks, metadata)

Feature Pipeline (new focus area)
  ├─ Angles/FingerAngleBuffer
  │     └─ compute_smoothed_finger_angles()
  │           -> populates HandData.joint_angles / finger summaries
  └─ Other per-hand features (pinch, palm plane, etc.)
        (goal: all centralized here instead of scattered helpers)

Classifier / Gesture Logic
  ├─ GestureClassifier.classify_single(hand)
  │     └─ consumes HandData.*
  │        - uses smoothed angles for curls/poses
  │        - maintains history (EMA/hysteresis)
  └─ Future: multi-hand gestures built on shared summaries

Debug & Visualization
  ├─ main_loop capture/classifier threads
  │     └─ draw_hand_debug(), draw_joint_angle_labels()
  │           -> read only from HandData (no extra computation)
  └─ Boundaries/annotators (stay consumers)

Networking / Output
  └─ GestureServer (hand.gesture -> external engine)

Refactor checkpoints
1. “HandData Feature Layer”: add a dedicated step after HandTracker that runs all feature generators (angles, lengths, pinch metrics) and writes results into HandData once per frame.
2. Remove redundant calculations (curl/angles) from GestureClassifier/helpers; rely on the feature layer outputs.
3. Store smoothing buffers per hand inside the classifier (or hand manager) so both gestures and debug overlay reuse the same history.
4. Extend GestureClassifier to read the summarized finger states and implement the new gestures.

This keeps data flowing strictly: sensor → HandData → feature layer → classifier/output, with debug just observing the processed data.