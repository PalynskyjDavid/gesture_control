#pragma once
#include "InputBackend.h"

class PlatformFactory
{
public:
    static InputBackend *createBackend();
};
