#pragma once

class InputBackend
{
public:
    virtual ~InputBackend() = default;

    // Absolute mouse movement
    virtual void moveAbsolute(int x, int y) = 0;

    // Relative movement
    virtual void moveRelative(int dx, int dy) = 0;

    // Clicks
    virtual void leftClick() = 0;
    virtual void rightClick() = 0;
    virtual void doubleClick() = 0;

    // Button press + release (for drag)
    virtual void mouseDown() = 0;
    virtual void mouseUp() = 0;

    virtual void mouseDownRight() = 0;
    virtual void mouseUpRight() = 0;

    // Scrolling
    virtual void scroll(int delta) = 0;
};
