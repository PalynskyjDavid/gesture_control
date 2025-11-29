#pragma once
#include <QString>

struct HandInfo
{
    QString handedness;
    bool visible = false;

    QString gesture;
    float confidence = 0.0f;

    float pinchDistance = 0.0f;
    float thumbAngle = 0.0f;

    bool curls[4] = {false, false, false, false};

    float wristX = 0.0f;
    float wristY = 0.0f;
    float wristZ = 0.0f;
};
