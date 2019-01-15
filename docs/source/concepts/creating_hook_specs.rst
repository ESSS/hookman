.. _creating-hook-specs-section:

Creating HookSpecs
===================

In order to inform to ``HookMan`` which Hooks are available in your application, it's necessary to create a :ref:`hook-specs-api-section` object.


.. code-block:: python

    from hookman.hooks import HookSpecs

    def env_temperature(arg1: 'float', arg2: 'float') -> 'float':
        """
        Docs for Environment Temperature
        """

    specs = HookSpecs(
        project_name='Acme',
        version='1',
        pyd_name='_alfasim_hooks',
        hooks=[
            env_temperature,
        ]
    )

This object has the following fields:

- **Project Name**:
    An display name to be used to identify the project and to name the hook functions.
- **Version**:
    Current version of the spec, when a new hook is created or modified this version should be incremented
- **pyd_name**:
    Name of the module exported by ``PyBind11`` on ``HookCallerPython.cpp`` file.
- **Hooks**:
    A list with the hooks available for the project, each hook is represented by a python function.


The field hooks should be a list of Python functions, with the following fields filled:

    - **Function Name**: The name of hook.
    - **Arguments**: The arguments that the Hooks will receive.
    - **Type Hints**: The type of argument type.
    - **Doc String**: The docummentation of the Hook.

Noticed that all the fields are necessary in order to create the :ref:`hook-specs-api-section` object,
if any of the fiels are not correctly informed a ``TypeError`` exception will be raised
