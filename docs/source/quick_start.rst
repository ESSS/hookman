.. _quick-start-section:

Quick Start
===========

As mentioned before, ``HookMan`` is a python application that uses plugins written in C/C++.

In order to use this project in your application, it's necessary to create a configuration object named ``HooksSpecs``. 
This object provides pieces of information related to which hooks are available and which arguments are expected to be sent or received.

The block code below exemplifies a valid HooksSpecs configuration:


.. code-block:: python

    from hookman.hooks import HooksSpecs

    def env_temperature(arg1: 'float', arg2: 'float') -> 'float':
        """
        Docs for Environment Temperature
        """

    specs = HooksSpecs(
        project_name='Acme',
        version='1',
        pyd_name='_alfasim_hooks',
        hooks=[
            env_temperature,
        ]
    )

With the HookSpecs defined, it's possible to generate the project files, necessary for the application as well as plugins templates.

.. code-block:: python

    # Initializing a class 
    hook_gen = HookManGenerator(hook_spec_file_path=Path('hook_specs.py'))
    hook_gen.generate_project_files(dst_path=<dst_dir>)


The command above will create the following files:

- HookCaller.hpp
- HookCallerPython.cpp
- CMakeLists.txt

These files contain all the code necessary to make the project ``PyBind11_`` integrates with your application, and the CMakeLists file contains a boilerplate
to generate an ``pyd`` file.

.. important::

    Noticed that the macro ``PYBIND11_MODULE`` (on ``HookCallerPython.cpp``) defines the module name that should be used to import these bindings, 
    and this name is used on the ``HookSpecs`` object with the field "pyd_name".


With the files generated, and compiled. It's possible now to get an instance of the ``HookCaller`` object from that holds all information related with the hooks implementation.

.. code-block:: python

    from acme_project import specs

    # Initializing a class 
    hook_manager = HookMan(specs=specs, plugin_dirs=['path1','path2'])

    hook_caller = hook_manager.get_hook_caller()

    # Getting access to the hook implementation
    hook_caller.friction_factor()
    hook_caller.env_temperature()

    # Checking if the hook was implemented
    assert friction_factor is not None
    assert env_temperature is None

The object ``hook_caller`` contains all references for the functions implemented on the plugins, you can access these methods directly or pass this reference
to another module or a C++ application.

The example below shows how to execute the method in a python module.

.. code-block:: python

    from acme_project import specs

    # Initializing a class 
    hook_manager = HookMan(specs=specs, plugin_dirs=['path1','path2'])
    hook_caller = hook_manager.get_hook_caller()

    # Getting access to the hook implementation
    friction_factor_function = hook_caller.friction_factor()

    #Executing the method implemented in one of the plugins.
    friction_factor_function(argument1, argument2).


.. _PyBind11: https://github.com/pybind/pybind11