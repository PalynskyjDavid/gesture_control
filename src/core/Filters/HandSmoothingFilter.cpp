#include "HandSmoothingFilter.h"

void HandSmoothingFilter::update(const QString &hand,
                                 float x, float y, float z, float angle)
{
    SmoothData &d = data_[hand];

    if (!d.initialized)
    {
        d = {true, x, y, z, angle};
        return;
    }

    d.x = alpha_ * x + (1 - alpha_) * d.x;
    d.y = alpha_ * y + (1 - alpha_) * d.y;
    d.z = alpha_ * z + (1 - alpha_) * d.z;
    d.angle = alpha_ * angle + (1 - alpha_) * d.angle;
}

void HandSmoothingFilter::getSmoothed(const QString &hand,
                                      float &x, float &y,
                                      float &z, float &angle) const
{
    if (!data_.contains(hand))
        return;

    const SmoothData &d = data_[hand];
    x = d.x;
    y = d.y;
    z = d.z;
    angle = d.angle;
}
