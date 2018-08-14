if (NOT "$ENV{CONDA_PREFIX}" STREQUAL "")
    if(WIN32)
        string(REPLACE "\\" "/" _CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}/Library")
        string(REPLACE "\\" "/" _PYTHON_DIR "$ENV{CONDA_PREFIX}")
        set(CMAKE_PREFIX_PATH "${_CMAKE_PREFIX_PATH}" CACHE PATH "prefix path")
        set(PYTHON_DIR "${_PYTHON_DIR}" CACHE PATH "python directory")
    elseif(UNIX)
        set(CMAKE_PREFIX_PATH $ENV{CONDA_PREFIX} CACHE PATH "prefix path")
        set(PYTHON_DIR $ENV{CONDA_PREFIX} CACHE PATH "python directory")
    endif()

    message(STATUS "Conda detected. CMAKE_PREFIX_PATH set to: ${CMAKE_PREFIX_PATH}")
else()
    # Add support for `pybind11` in CMake trough an environment variable, this configuration is currently used on appveyor
  if(NOT "$ENV{PYBIND_PATH}" STREQUAL "")
    set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "$ENV{PYBIND_PATH}")
  endif()
endif()


# Add support for `pybind11` in CMake (cmake modules coming from `conda-forge`).
if(WIN32)
    # On Windows, these packages are not installing things under `<env>/Library/...`, which would be the correct place.
    # This fixes things.
    set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_PREFIX_PATH}/../share/cmake/pybind11")
else()
    set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_PREFIX_PATH}/share/cmake/pybind11")
endif()

message(STATUS "(3) CMAKE_MODULE_PATH: ${CMAKE_MODULE_PATH}")


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


