.. _creating-plugin-section:

Creating plugins
================


A plugin consists of a ``ZipFile`` with the extension ``.hmplugin`` that has the following folder hierarchy.


.. code-block:: Bash

    \---<plugin_id>
        |
        +---assets
        |       plugin.yaml
        |       README.md
        |
        \---artifacts
                Linux:    lib<plugin_id>.so
                Windows:  <plugin_id>.dll


The ``HookMan`` project has some utilities to help with the task to generate plugins for the user.

To generate the initial boilerplate for a plugin, execute:

.. code-block:: bash

    $ python -m hookman generate-plugin-template <specs-path> <plugin-name> <shared-lib-name> <author-name> <author-email> [dst-path]

The arguments are:

- **specs-path**:
    Path to the ``hook_specs.py`` file of the application
- **plugin-name**:
    Name of the plugin to be displayed
- **shared-lib-name**:
    The filename of the compiled plugin
- **author-name**:
    Name of the plugin author to be displayed
- **author-email**:
    Email of the plugin author to be displayed
- **dst-path**:
    A path to where the template generated should be placed, if not given the current directory will be used


The generated template has the following structure:


.. code-block:: bash

    \---<plugin_id>
        |   compile.py
        |   CMakeLists.txt
        |
        +---assets
        |       plugin.yaml
        |       README.md
        |
        \---src
                CMakeLists.txt
                hook_specs.h
                plugin.c


Where:

- **plugin.yaml**:
    File with necessary information about the plugin to the application using this plugin
- **plugin.c**
    The source file of the plugin
- **hook_specs.h**
    The header file with all the information necessary to create a plugin for the given application
- **CMakeLists**
    CMake file with the minimum configuration necessary to build a shared library across different platforms
- **README**
    Readme file with the description of the Plugin, to be used by the application.
- **compile.py**
    Script file to generate the shared library, this command will create a folder name artifacts.


Distributing
------------

Plugins should be packaged for distribution and installation in the target software. HookMan plugins are deployed
with the ``.hmplugin`` extension, which is a zip file with the binaries and assets necessary for execution.

To create a ``.hmplugin`` extension, use this command:

.. code-block:: bash

    $ python -m hookman package-plugin <specs-path> <package-name> <plugin-dir> [dst-path]

Where:

- **specs-path**:
    Path to the ``hook_specs.py`` file of the application
- **package-name**:
    Output name of the package file, without extension. For example: ``myplugin-1.0``
- **plugin-dir**:
    Directory where the plugin is located
- **plugin-dir**:
    Directory where the plugin is located
- **dst-path**:
    A path to where put the generated package file, if not given the package will be generated in the same directory
    as ``plugin-dir``.
