# Gesture Control – Full Working Project

This is a complete multi-platform Qt/C++ gesture control application using:

- **Qt6** (Widgets + Network)
- **MediaPipe (Python)** for hand tracking
- **TCP/CSV protocol** for sending gestures to C++
- **Platform abstraction backend**
- **JSON binding persistence**
- **Smooth wrist tracking + gesture recognition**

---

# 🚀 Build Instructions (Windows)

### Requirements
- Visual Studio 2022 (Community or Build Tools)
- Qt 6.6+ (msvc2022_64 build)
- CMake 3.16+
- Python 3.10 with:




pip install mediapipe opencv-python

### Build Steps

Open **x64 Native Tools Command Prompt for VS 2022**:

```bash
cd gesture_control_full_project
cmake -B build -S . -G "Visual Studio 17 2022"
cmake --build build --config Debug

Run the app:
build/Debug/gesture_control.exe



Running the Hand Tracking Server
cd python
py -3.10 gesture_server.py


# 📁 Final Project Structure

```
    gesture_control/
    │
    ├── CMakeLists.txt
    ├── docs/
    ├── python/
    │   ├── gesture_server.py
    │   ├── HandData               # all hand values
    │   ├── GestureClassifier      # pinch/fist/open logic
    │   ├── HandTracker            # mediapipe interaction
    │   ├── GestureServer          # TCP code
    │   └── main_loop()            # ties everything together
    └── src/
        ├── main.cpp
        ├── ui/
        │   ├── MainWindow.h
        │   └── MainWindow.cpp
        │
        ├── core/
        │   ├── GestureEngine.cpp
        │   ├── GestureEngine.h
        │   ├── GestureStateMachine.cpp
        │   ├── GestureStateMachine.h
        │   └── Filters/
        │       ├── HandSmoothingFilter.cpp
        │       └── HandSmoothingFilter.h
        │
        ├── network/
        │   ├── TcpClient.cpp
        │   ├── TcpClient.h
        │   ├── MessageParser.cpp
        │   └── MessageParser.h
        │
        ├── platform/
        │   ├── InputBackend.h
        │   ├── InputSimulator.h
        │   ├── PlatformFactory.cpp
        │   ├── PlatformFactory.h
        │   ├── windows/ (working WinAPI mouse)
        │   ├── linux/   (stubs)
        │   └── mac/     (stubs)
        │
        └── common/
            ├── Types.h
            ├── Constants.h
            ├── Utils.h
            └── Utils.cpp
```
