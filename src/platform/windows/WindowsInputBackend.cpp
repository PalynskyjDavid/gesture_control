#include "WindowsInputBackend.h"

static void sendMouse(DWORD flags, int dx = 0, int dy = 0, DWORD data = 0)
{
    INPUT in = {};
    in.type = INPUT_MOUSE;
    in.mi.dwFlags = flags;

    in.mi.dx = dx;
    in.mi.dy = dy;
    in.mi.mouseData = data;

    SendInput(1, &in, sizeof(INPUT));
}

void WindowsInputBackend::moveAbsolute(int x, int y)
{
    int mx = (x * 65535) / GetSystemMetrics(SM_CXSCREEN);
    int my = (y * 65535) / GetSystemMetrics(SM_CYSCREEN);

    sendMouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, mx, my);
}

void WindowsInputBackend::moveRelative(int dx, int dy)
{
    sendMouse(MOUSEEVENTF_MOVE, dx, dy);
}

void WindowsInputBackend::leftClick()
{
    mouseDown();
    mouseUp();
}

void WindowsInputBackend::rightClick()
{
    mouseDownRight();
    mouseUpRight();
}

void WindowsInputBackend::doubleClick()
{
    leftClick();
    Sleep(50);
    leftClick();
}

void WindowsInputBackend::mouseDown()
{
    sendMouse(MOUSEEVENTF_LEFTDOWN);
}

void WindowsInputBackend::mouseUp()
{
    sendMouse(MOUSEEVENTF_LEFTUP);
}

void WindowsInputBackend::mouseDownRight()
{
    sendMouse(MOUSEEVENTF_RIGHTDOWN);
}

void WindowsInputBackend::mouseUpRight()
{
    sendMouse(MOUSEEVENTF_RIGHTUP);
}

void WindowsInputBackend::scroll(int delta)
{
    sendMouse(MOUSEEVENTF_WHEEL, 0, 0, delta);
}
