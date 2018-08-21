

``HookMan`` is a python package that provides to applications a plugin management system, 
enabling plugins/extensions written in C/C++ to interact with the application.


It was conceived to facilitate the application development, allowing hooks to be exposed in a
clear way and allowing plugins to be developed without access to classes or data from the application.


With ``HookMan`` your application can have access to the hooks implemented on plugins as simple as the example below.

.. code-block:: python

    # Initializing a class 
    hm = HookMan(specs=acme_specs, plugin_dirs=['path1','path2'])

    hook_caller = hm.get_hook_caller()

    # Getting access to the hook implementation
    hook_caller.friction_factor()
    hook_caller.env_temperature()

    # Checking if the hook was implemented
    assert friction_factor is not None
    assert env_temperature is None


How does it work?
-----------------

In order to use the ``HookMan`` project in your application, is necessary to inform which ``Hooks``
are available to be implemented through a configuration object.


With this configuration defined, users can create plugins to implements the ``Hooks`` available extending the behavior of your application.


All plugins informed to your application will be validated by HookMan (to check which hooks are implemented),
and an object holding a reference to the ``Hooks`` will be passed to the application.


The ``HookMan`` project uses the library PyBind11_ to interact between Python and C/C++,
allowing a straightforward usage for who is calling the function (either in Python or in C++).


Defining some terminologies:

- ``Application`` ⇨  The program that offers the extensions.
- ``Hook``        ⇨  An extension of the Application.
- ``Plugin``      ⇨  The program that implements the ``Hooks``.
- ``User``        ⇨  The person who installed the application.


.. _PyBind11: https://github.com/pybind/pybind11