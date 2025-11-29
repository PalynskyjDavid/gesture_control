#pragma once
#include "../InputBackend.h"

class LinuxInputBackend : public InputBackend
{
public:
    void moveAbsolute(int, int) override {}
    void moveRelative(int, int) override {}

    void leftClick() override {}
    void rightClick() override {}
    void doubleClick() override {}

    void mouseDown() override {}
    void mouseUp() override {}

    void mouseDownRight() override {}
    void mouseUpRight() override {}

    void scroll(int) override {}
};
