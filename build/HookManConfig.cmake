if("$ENV{CONDA_PREFIX}" STREQUAL "")
  file(TO_CMAKE_PATH "$ENV{TOX_ENV_DIR}" ENV_PREFIX)
  message(STATUS "ENV_PREFIX from tox: ${ENV_PREFIX}")
else()
file(TO_CMAKE_PATH "$ENV{CONDA_PREFIX}" ENV_PREFIX)
  message(STATUS "ENV_PREFIX from conda: ${ENV_PREFIX}")
endif()

if (NOT "$ENV_PREFIX" STREQUAL "")
    set(CMAKE_PREFIX_PATH "${ENV_PREFIX}" CACHE PATH "prefix path")
    set(PYTHON_DIR "${ENV_PREFIX}" CACHE PATH "python directory")
endif()

message(STATUS "CMAKE_PREFIX_PATH: ${CMAKE_PREFIX_PATH}")

if(NOT WIN32)
  # These must be configured after include(Config)
  set(CMAKE_C_FLAGS       "-Wall -std=c99")
  set(CMAKE_C_FLAGS_DEBUG "-g")

  execute_process(
    COMMAND gcc --print-libgcc-file-name
    OUTPUT_VARIABLE _LIBGCC_FILENAME
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )

  get_filename_component(GCC_BASE_DIR ${_LIBGCC_FILENAME} DIRECTORY)

  message(STATUS "Found GCC base directory: ${GCC_BASE_DIR}")

  set(CMAKE_CXX_FLAGS       "-Wall")
  set(CMAKE_CXX_LINK_FLAGS  "-lstdc++")
  set(CMAKE_CXX_FLAGS_DEBUG "-g")

endif(NOT WIN32)
