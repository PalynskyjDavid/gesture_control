#pragma once
#include "InputBackend.h"

class InputSimulator
{
public:
    explicit InputSimulator(InputBackend *backend)
        : backend_(backend) {}

    void moveAbsolute(int x, int y) { backend_->moveAbsolute(x, y); }
    void moveRelative(int dx, int dy) { backend_->moveRelative(dx, dy); }

    void leftClick() { backend_->leftClick(); }
    void rightClick() { backend_->rightClick(); }
    void doubleClick() { backend_->doubleClick(); }

    void mouseDown() { backend_->mouseDown(); }
    void mouseUp() { backend_->mouseUp(); }

    void mouseDownRight() { backend_->mouseDownRight(); }
    void mouseUpRight() { backend_->mouseUpRight(); }

    void scroll(int delta) { backend_->scroll(delta); }

private:
    InputBackend *backend_;
};
