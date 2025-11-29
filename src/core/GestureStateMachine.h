#pragma once
#include <QString>
#include <QMap>

/**
 * GestureStateMachine
 * --------------------
 * Prevents:
 *  - gesture jitter
 *  - repeated click events
 *
 * For each hand we track:
 *  - lastGesture
 *  - lastStableGesture
 *  - frame counter
 */

class GestureStateMachine
{
public:
    GestureStateMachine() = default;

    QString filterGesture(const QString &hand, const QString &rawGesture);

private:
    struct State
    {
        QString lastGesture;
        QString stableGesture;
        int framesStable = 0;
    };

    QMap<QString, State> perHand_;
};
