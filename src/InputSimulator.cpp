#include "InputSimulator.h"

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

InputSimulator::InputSimulator(QObject *parent)
    : QObject(parent)
{
}

void InputSimulator::moveRelative(int dx, int dy)
{
#ifdef _WIN32
    INPUT input = {};
    input.type = INPUT_MOUSE;
    input.mi.dx = dx;
    input.mi.dy = dy;
    input.mi.dwFlags = MOUSEEVENTF_MOVE;
    SendInput(1, &input, sizeof(INPUT));
#else
    Q_UNUSED(dx)
    Q_UNUSED(dy)
#endif
}

void InputSimulator::leftClick()
{
#ifdef _WIN32
    INPUT inputs[2] = {};

    inputs[0].type = INPUT_MOUSE;
    inputs[0].mi.dwFlags = MOUSEEVENTF_LEFTDOWN;

    inputs[1].type = INPUT_MOUSE;
    inputs[1].mi.dwFlags = MOUSEEVENTF_LEFTUP;

    SendInput(2, inputs, sizeof(INPUT));
#endif
}

void InputSimulator::rightClick()
{
#ifdef _WIN32
    INPUT inputs[2] = {};

    inputs[0].type = INPUT_MOUSE;
    inputs[0].mi.dwFlags = MOUSEEVENTF_RIGHTDOWN;

    inputs[1].type = INPUT_MOUSE;
    inputs[1].mi.dwFlags = MOUSEEVENTF_RIGHTUP;

    SendInput(2, inputs, sizeof(INPUT));
#endif
}

void InputSimulator::doubleClick()
{
    leftClick();
    leftClick();
}

void InputSimulator::scroll(int delta)
{
#ifdef _WIN32
    INPUT input = {};
    input.type = INPUT_MOUSE;
    input.mi.dwFlags = MOUSEEVENTF_WHEEL;
    input.mi.mouseData = delta; // 120 = one notch
    SendInput(1, &input, sizeof(INPUT));
#else
    Q_UNUSED(delta)
#endif
}
