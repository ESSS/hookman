.. _creating-plugin-section:

Creating plugins
================


A plugin consists of a ``ZipFile`` with the extension ``.hmplugin`` that has the following folder hierarchy.


.. code-block:: Bash

    \---<plugin_name>
        |
        +---assets
        |       config.yaml
        |       README.md
        |
        \---artifacts
                shared_lib_name<.so or .dll>


The ``HookMan`` project has some utilities to help with the task to generate plugins for the user.
The class :ref:`hookman-generator-api-section` has a method ``generate_plugin_template`` which generate a "boilerplate" for a plugin.

In order to call this method it's necessary to pass the following arguments:

- **plugin-name**: 
    Name of the plugin to be displayed
- **shared_lib_name**: 
    The filename of the compiled plugin
- **author_email**: 
    Name of the plugin author to be displayed
- **author_name**: 
    Email of the plugin author to be displayed
- **dst_path**: 
    A path to where the template generated should be placed, if not informed the current directory will be used.


The generated template has the following structure:


.. code-block:: bash

    \---<plugin_name>
        |   build.py
        |   CMakeLists.txt
        |
        +---assets
        |       config.yaml
        |       README.md
        |
        \---src
                CMakeLists.txt
                hook_specs.h
                plugin.c


Where:

- **config.yml**:
    File with necessary information about the plugin to the application using this plugin
- **plugin.c**	
    The source file of the plugin
- **hook_specs.h**	
    The header file with all the information necessary to create a plugin for the given application
- **CMakeLists**	
    CMake file with the minimum configuration necessary to build a shared library across different platforms
- **README**	
    Readme file with the description of the Plugin, to be used by the application.
- **build.py**	
    Script file to generate the shared library, this command will create a folder name artifacts.


In order to create a ``.hmplugin`` the same class, The class :ref:`hookman-generator-api-section`, 
has a method named ``generate_package`` which generate a ``.hmplugin`` file as output.