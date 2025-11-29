#pragma once
#include "../InputBackend.h"
#include <windows.h>

class WindowsInputBackend : public InputBackend
{
public:
    WindowsInputBackend() = default;

    void moveAbsolute(int x, int y) override;
    void moveRelative(int dx, int dy) override;

    void leftClick() override;
    void rightClick() override;
    void doubleClick() override;

    void mouseDown() override;
    void mouseUp() override;

    void mouseDownRight() override;
    void mouseUpRight() override;

    void scroll(int delta) override;
};
