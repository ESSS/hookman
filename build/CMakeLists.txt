cmake_minimum_required(VERSION 3.5.2)

set(CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR})
set(LIBS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/artifacts)
set(PROJECT_NAME hookman)
set(ARTIFACTS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/artifacts)

if(NOT WIN32)
  set(CMAKE_C_COMPILER    clang)
  set(CMAKE_CXX_COMPILER  clang++)
endif(NOT WIN32)

project (hookman LANGUAGES CXX C)

include(HookManConfig)

set(CMAKE_C_STANDARD 99)

add_subdirectory(build_directory_for_tests/)


