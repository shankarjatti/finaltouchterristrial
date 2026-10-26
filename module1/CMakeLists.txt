cmake_minimum_required(VERSION 3.10)
project(securecom_module1 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release)
set(CMAKE_CXX_FLAGS_RELEASE "-O2")

# ── UHD ──────────────────────────────────────────────────────────────────────
find_package(UHD 4.0 REQUIRED)
include_directories(${UHD_INCLUDE_DIRS})

# ── Threads ──────────────────────────────────────────────────────────────────
find_package(Threads REQUIRED)

# ── Sources ───────────────────────────────────────────────────────────────────
set(SOURCES
    src/main.cpp
    src/usrp_controller.cpp
    src/burst_controller.cpp
    src/tcp_server.cpp
)

add_executable(securecom_module1 ${SOURCES})

target_include_directories(securecom_module1 PRIVATE src)

target_link_libraries(securecom_module1
    PRIVATE
    ${UHD_LIBRARIES}
    Threads::Threads
)

message(STATUS "UHD Version  : ${UHD_VERSION}")
message(STATUS "UHD Includes : ${UHD_INCLUDE_DIRS}")
message(STATUS "UHD Libs     : ${UHD_LIBRARIES}")
