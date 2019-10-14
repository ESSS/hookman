.. _quick-start-section:

Quick Start
===========

As previously mentioned, ``HookMan`` is a python application that uses plugins written in C/C++.

In order to integrate this project in your application, it's necessary to create a configuration object named :ref:`hook-specs-api-section`.
This object provides pieces of information related to which hooks are available and which arguments are expected to be sent or received.

The block code below exemplifies a valid :ref:`hook-specs-api-section` configuration:


.. code-block:: python

    from hookman.hooks import HookSpecs

    def env_temperature(arg1: 'double', arg2: 'double') -> 'double':
        """
        Docs for Environment Temperature
        """

    def friction_factor(arg1: 'int', arg2: 'double') -> 'double':
        """
        Docs for Friction Factor
        """

    specs = HookSpecs(
        project_name='Acme',
        version='1',
        pyd_name='_alfasim_hooks',
        hooks=[
            env_temperature,
            friction_factor,
        ]
    )

With the :ref:`hook-specs-api-section` defined, it's possible to generate the necessary files to interact between the application and the plugins implementation.

.. code-block:: bash

    $ python -m hookman generate-project-files hook_specs.py --dst-path <DEST_DIR>

The output from the command above will be the following files:

- HookCaller.hpp
- HookCallerPython.cpp
- CMakeLists.txt

These files contain all code necessary to make the project ``pybind11_`` integrates with your application, and the CMakeLists file contains a boilerplate
to compile and generate the binary extensions (``.pyd`` file)

.. important::

    Noticed that the macro ``PYBIND11_MODULE`` (on ``HookCallerPython.cpp``) defines the module name that should be used to import these bindings,
    and this name is used on the :ref:`hook-specs-api-section` object with the field "pyd_name".


With the files generated, and compiled., it's possible now to get an instance of the ``HookCaller`` object that holds all information related with the hooks implementation.

.. code-block:: python

    from acme_project import specs

    # Initializing a class
    hook_manager = HookMan(specs=specs, plugin_dirs=['path1', 'path2'])

    hook_caller = hook_manager.get_hook_caller()

    # Getting access to the hook implementation
    friction_factor = hook_caller.friction_factor()
    env_temperature = hook_caller.env_temperature()

    # Checking if the hook was implemented
    assert friction_factor is not None
    assert env_temperature is None

The object ``hook_caller`` contains all references for the functions implemented in the plugins,
you can access these methods directly or pass this reference to another module or a C++ function.

Executing in python
--------------------

The example below shows how to execute the method in a python module.

.. code-block:: python

    from acme_project import specs

    # Initializing a class
    hook_manager = HookMan(specs=specs, plugin_dirs=['path1', 'path2'])
    hook_caller = hook_manager.get_hook_caller()

    # Getting access to the hook implementation
    friction_factor_function = hook_caller.friction_factor()

    #Executing the method implemented in one of the plugins.
    ff_result = friction_factor_function(1, 2.5).

    print(f"Result from friction_factor hook: {ff_result}")

Executing in C++
--------------------

As mentioned on the `pybind11 functional documentation`_, the C++11 standard brought the generic polymorphic function wrapper ``std::function<>``
, which enable powerful new ways of working with functions.


.. code-block:: cpp
   :caption: Example of a C++ function that takes an arbitrary function and execute it.
   :name: aa-py

    int friction_factor(const std::function<double(int, double)> &f) {
        return f(10, 2.5);
    }

With the binding code for this function in place, it's possible to pass a function implemented
on one of the plugins directly to C++.

.. code-block:: cpp
   :caption: binding_code.cpp

   #include <pybind11/functional.h>

    PYBIND11_MODULE(my_cpp_binding_module, m) {
        m.def("func_friction_factor", &friction_factor);

    }

The example below shows how to create an object ``hook_caller``,
and pass a function implemented on one of the plugins directly to C++ a function.

.. code-block:: python

    from acme_project import specs

    # Initializing a class
    hook_manager = HookMan(specs=specs, plugin_dirs=['path1', 'path2'])
    hook_caller = hook_manager.get_hook_caller()

    # Getting access to the hook implementation
    friction_factor_function = hook_caller.friction_factor()

    # Importing the binding with the cpp code
    import my_cpp_binding_module

    # Passing the Friction Factor function to C++
    my_cpp_binding_module.func_friction_factor(friction_factor_function)


.. _pybind11: https://github.com/pybind/pybind11
.. _`pybind11 functional documentation`: https://pybind11.readthedocs.io/en/stable/advanced/cast/functional.html
