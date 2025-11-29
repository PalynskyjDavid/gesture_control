#pragma once

#include <QString>
#include <QStringList>
#include <QElapsedTimer>

/**
 * Generic helpers used across modules.
 */

namespace Utils
{

    inline QStringList splitCSV(const QString &msg)
    {
        return msg.split(',', Qt::SkipEmptyParts);
    }

    inline float clamp(float v, float min, float max)
    {
        if (v < min)
            return min;
        if (v > max)
            return max;
        return v;
    }

    // FPS timer for debugging performance
    class FPSTimer
    {
    public:
        FPSTimer()
        {
            timer_.start();
        }

        float fps()
        {
            qint64 ms = timer_.restart();
            if (ms <= 0)
                return 0.f;
            return 1000.f / ms;
        }

    private:
        QElapsedTimer timer_;
    };
}
