#pragma once

#include <QObject>

class InputSimulator : public QObject
{
    Q_OBJECT

public:
    explicit InputSimulator(QObject *parent = nullptr);

    void moveRelative(int dx, int dy);
    void leftClick();
    void rightClick();
    void doubleClick();
    void scroll(int delta); // positive = up, negative = down
};
