

``HookMan`` is a python package that provides a plugin management system to applications, 
specially those who are written (in totally or partially) in C++. 

It enables external contributors to implement plugins which act as extensions written in C/C++ 
that interact with the application through well-defined *hooks*.

This system was largely inspired by `pluggy`_, 
the plugin system which powers `pytest`_, `tox`_, and `devpi`_, but with the intent to be called 
from a C++ application rather than from Python.

It was conceived to facilitate the application development, allowing hooks to be exposed in a
clear way and allowing plugins to be developed without access to classes or data from the application.

With ``HookMan`` your application can have access to the hooks implemented on plugins as simple as the example below.

.. code-block:: python

    # Initializing a class 
    hm = HookMan(specs=acme_specs, plugin_dirs=['path1','path2'])

    hook_caller = hm.get_hook_caller()

    # Getting access to the hook implementation
    friction_factor = hook_caller.friction_factor()
    env_temperature = hook_caller.env_temperature()

    # Checking if the hook was implemented
    assert friction_factor is not None
    assert env_temperature is None


How does it work?
-----------------

In order to use ``HookMan`` in your application, it is necessary to inform which ``Hooks``
are available to be implemented through a configuration object.


With this configuration defined, users can create plugins that implement available ``Hooks`` extending the behavior of your application.


All plugins informed to your application will be validated by HookMan (to check which hooks are implemented),
and an object holding a reference to the ``Hooks`` will be passed to the application.


The ``HookMan`` project uses the library PyBind11_ to interact between Python and C/C++,
allowing a straightforward usage for who is calling the function (either in Python or in C++).


Defining some terminologies:

- ``Application`` ⇨  The program that offers the extensions.
- ``Hook``        ⇨  An extension of the Application.
- ``Plugin``      ⇨  The program that implements the ``Hooks``.
- ``User``        ⇨  The person who installed the application.


.. _PyBind11:   https://github.com/pybind/pybind11
.. _pluggy:     https://github.com/pytest-dev/pluggy
.. _pytest:     https://github.com/pytest-dev/pytest
.. _tox:        https://github.com/tox-dev/tox
.. _devpi:       https://github.com/devpi/devpi
