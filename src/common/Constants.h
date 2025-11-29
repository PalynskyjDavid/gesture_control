#pragma once

// Exponential smoothing factor for hand tracking
static constexpr float SMOOTHING_ALPHA = 0.9f;

// Number of stable frames required for gesture change
static constexpr int GESTURE_STABLE_FRAMES = 3;

// Networking defaults
static constexpr int PYTHON_SERVER_PORT = 5555;
static constexpr const char *PYTHON_SERVER_IP = "127.0.0.1";

// Confidence required to consider hand usable
static constexpr float MIN_CONFIDENCE = 0.65f;
