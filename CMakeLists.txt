cmake_minimum_required(VERSION 3.16)
project(GestureControl LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt auto-moc/uic/rcc
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

# Find Qt
find_package(Qt6 COMPONENTS Widgets REQUIRED)

# Find ZeroMQ via vcpkg
find_package(ZeroMQ CONFIG REQUIRED)

set(SOURCES
    src/main.cpp
    src/MainWindow.cpp
    src/GestureEngine.cpp
    src/InputSimulator.cpp
)

set(HEADERS
    src/MainWindow.h
    src/GestureEngine.h
    src/InputSimulator.h
)

add_executable(GestureControl
    ${SOURCES}
    ${HEADERS}
)

target_link_libraries(GestureControl
    PRIVATE
        Qt6::Widgets
        libzmq
)

if (WIN32)
    set_target_properties(GestureControl PROPERTIES WIN32_EXECUTABLE TRUE)
endif()
