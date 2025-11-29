#pragma once
#include <QString>
#include <QMap>

/**
 * HandSmoothingFilter
 * --------------------------
 * Per-hand exponential smoothing of:
 *  - x, y, z coordinates
 *  - angle
 */

class HandSmoothingFilter
{
public:
    HandSmoothingFilter(float alpha = 0.25f)
        : alpha_(alpha) {}

    void update(const QString &hand,
                float x, float y, float z, float angle);

    void getSmoothed(const QString &hand,
                     float &x, float &y, float &z, float &angle) const;

private:
    struct SmoothData
    {
        bool initialized = false;
        float x, y, z, angle;
    };

    float alpha_;
    QMap<QString, SmoothData> data_;
};
