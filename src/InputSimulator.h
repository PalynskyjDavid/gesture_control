#pragma once

#include <memory>

#include <QObject>

class InputBackend;

class InputSimulator : public QObject
{
    Q_OBJECT

public:
    explicit InputSimulator(QObject *parent = nullptr);
    ~InputSimulator();

    bool isReady() const;

    void moveAbsolute(int x, int y);
    void moveRelative(int dx, int dy);
    void leftClick();
    void rightClick();
    void doubleClick();
    void scroll(int delta); // positive = up, negative = down

private:
    void ensureBackend();

    std::unique_ptr<InputBackend> backend_;
};
