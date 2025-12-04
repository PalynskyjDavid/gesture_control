#include "InputSimulator.h"

#include <QDebug>

#include "platform/InputBackend.h"
#include "platform/PlatformFactory.h"

InputSimulator::InputSimulator(QObject *parent)
    : QObject(parent)
{
    ensureBackend();
}

InputSimulator::~InputSimulator() = default;

bool InputSimulator::isReady() const
{
    return backend_ != nullptr;
}

void InputSimulator::ensureBackend()
{
    if (backend_)
        return;

    backend_.reset(PlatformFactory::createBackend());
    if (!backend_)
    {
        qWarning() << "[InputSimulator] No platform backend available.";
    }
}

void InputSimulator::moveAbsolute(int x, int y)
{
    ensureBackend();
    if (backend_)
        backend_->moveAbsolute(x, y);
}

void InputSimulator::moveRelative(int dx, int dy)
{
    ensureBackend();
    if (backend_)
        backend_->moveRelative(dx, dy);
}

void InputSimulator::leftClick()
{
    ensureBackend();
    if (backend_)
        backend_->leftClick();
}

void InputSimulator::rightClick()
{
    ensureBackend();
    if (backend_)
        backend_->rightClick();
}

void InputSimulator::doubleClick()
{
    ensureBackend();
    if (backend_)
        backend_->doubleClick();
}

void InputSimulator::scroll(int delta)
{
    ensureBackend();
    if (backend_)
        backend_->scroll(delta);
}
