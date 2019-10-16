cmake_minimum_required(VERSION 3.5.2)

set(CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR})
set(LIBS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/artifacts)
set(PROJECT_NAME hookman)
set(ARTIFACTS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/artifacts)

include(HookManConfig)

project (hookman LANGUAGES CXX C)

#include(HookManConfig)

set(CMAKE_C_STANDARD 99)

add_subdirectory(build_directory_for_tests/)


