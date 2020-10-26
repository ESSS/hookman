=======
Hookman
=======

.. image:: https://img.shields.io/pypi/v/python-hookman.svg
    :target: https://pypi.python.org/pypi/python-hookman

.. image:: https://img.shields.io/conda/vn/conda-forge/python-hookman.svg
    :target: https://anaconda.org/conda-forge/python-hookman

.. image:: https://img.shields.io/pypi/pyversions/python-hookman.svg
    :target: https://pypi.org/project/python-hookman

.. image:: https://codecov.io/gh/ESSS/hookman/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/ESSS/hookman

.. image:: https://github.com/ESSS/hookman/workflows/Hookman%20-%20CI/badge.svg
    :target: https://github.com/ESSS/hookman/actions

.. image:: https://readthedocs.org/projects/hookman/badge/?version=latest
    :target: https://hookman.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status


This documentation covers HookMan usage & API.

For information about HookMan,  read the section above. For public changelog and how the project is maintained, please check the `GitHub page`_

What is HookMan?
================

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

    # Executing the hook, wherever it is implemented either in plugin A or B.
    ff_result = friction_factor(1, 2.5)
    env_tmp_result = env_temperature(35.5, 45.5)

How does it work?
-----------------

In order to use ``HookMan`` in your application, it is necessary to inform which ``Hooks``
are available to be implemented through a configuration object.


With this configuration defined, users can create plugins that implement available ``Hooks`` extending the behavior of your application.


All plugins informed to your application will be validated by HookMan (to check which hooks are implemented),
and an object holding a reference to the ``Hooks`` will be passed to the application.


The ``HookMan`` project uses the library pybind11_ to interact between Python and C/C++,
allowing a straightforward usage for who is calling the function (either in Python or in C++).


Defining some terminologies:

- ``Application`` ⇨  The program that offers the extensions.
- ``Hook``        ⇨  An extension of the Application.
- ``Plugin``      ⇨  The program that implements the ``Hooks``.
- ``User``        ⇨  The person who installed the application.




`Read the docs to learn more!`_

* Documentation: https://hookman.readthedocs.io.
* Free software: MIT license


Credits
-------
Thanks for pluggy_,  which is a similar project (plugin system) and source for many ideas.

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.


.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`GitHub page` :                   https://github.com/ESSS/hookman
.. _`read the docs to learn more!` :  https://hookman.readthedocs.io
.. _Cookiecutter:                     https://github.com/audreyr/cookiecutter
.. _devpi:                            https://github.com/devpi/devpi
.. _pluggy:                           https://github.com/pytest-dev/pluggy
.. _pybind11:                         https://github.com/pybind/pybind11
.. _pytest:                           https://github.com/pytest-dev/pytest
.. _tox:                              https://github.com/tox-dev/tox
