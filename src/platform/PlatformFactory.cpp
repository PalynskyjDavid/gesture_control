#include "PlatformFactory.h"

#ifdef _WIN32
#include "windows/WindowsInputBackend.h"
#elif __linux__
#include "linux/LinuxInputBackend.h"
#elif __APPLE__
#include "mac/MacInputBackend.h"
#endif

InputBackend *PlatformFactory::createBackend()
{
#ifdef _WIN32
    return new WindowsInputBackend();
#elif __linux__
    return new LinuxInputBackend();
#elif __APPLE__
    return new MacInputBackend();
#else
    return nullptr;
#endif
}
