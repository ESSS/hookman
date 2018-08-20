.. _creating-plugin-section:

Creating Plugins
================

Method generate_plugin_template
With the command generate_plugin_template, it's possible to create a "boilerplate" for a plugin.
In order to call this methos it's necessary to pass the following arguments:

Argument	Description
plugin_name	Name of the plugin to be displayed
shared_lib_name	The filename of the compiled plugin
author_email	Name of the plugin author to be displayed
author_name	Email of the plugin author to be displayed
dst_path	Path to where the template generated should be placed
The generated template has the following structure:

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
The description for each file can be checked bellow:

File	Description
config.yml	File with necessary information about the plugin to the application using this plugin
plugin.c	Source file of the plugin
hook_specs.h	Header file with all the information necessary to create a plugin for the given application
CMakeLists	CMake file with the minimum configuration necessary to build a shared library across different platforms
README	Readme file with the description of the Plugin, to be used by the application.
build.py	Script file to generate the shared library, this command will create a folder name artifacts.
Method generate_plugin_package