cmake_minimum_required(VERSION 3.5.2)

set(CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR})
set(LIBS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/libs)
set(PROJECT_NAME hookman)

if(NOT WIN32)
  set(CMAKE_C_COMPILER    gcc-7)
  set(CMAKE_CXX_COMPILER  g++-7)
endif(NOT WIN32)

project (hookman LANGUAGES CXX C)

include(HookManConfig)

set(CMAKE_C_STANDARD 99)

add_subdirectory(build_test/)


