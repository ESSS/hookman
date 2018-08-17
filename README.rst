=======
Hookman
=======

.. image:: https://img.shields.io/travis/esss/hookman.svg
        :target: https://travis-ci.org/esss/hookman

.. image:: https://readthedocs.org/projects/hookman/badge/?version=latest
        :target: https://hookman.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

``HookMan`` is a python package that helps applications to have plugins/extensions written in C/C++,
to improve the behaviour from the application.


It was conceived to facilitate the application development, allowing hooks to be exposed in a
clear way and allowing plugins to be developed without access to classes or data from the application.

.. note::
    ``HookMan`` is a Python 3.6+ application.

How does it work?
-----------------

In order to use the ``HookMan`` project in your application, is necessary to inform which ``Hooks``
are available to be implemented through a configuration object.


With this configuration defined, users can create plugins to implements the ``Hooks`` available extending the behavior of your application.


All plugins informed to your application will be validated by HookMan (to check which hooks are implemented),
and an object holding a reference to the ``Hooks`` will be passed to the application.


The ``HookMan`` project uses the library PyBind11__ to interact between Python and C/C++,
allowing a straightforward usage for who is calling the function (either in Python or in CPP).


Defining some terminologies:

- ``Application`` ⇨  The program that offers the extensions.
- ``Hook``        ⇨  An extension of the Application.
- ``Plugin``      ⇨  The program that implements the ``Hooks``.
- ``User``        ⇨  The person who installed the application.


For more details, `read the docs to learn more!`_

* Free software: MIT license
* Documentation: https://hookman.readthedocs.io.


Features
--------

* TODO

* Free software: MIT license

Credits
-------
Thanks for Pluggy_,  which is a similar project (plugin system) and source for many ideas.

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.


.. _`read the docs to learn more!` : https://hookman.readthedocs.io.
.. _PyBind11: https://github.com/pybind/pybind11
.. _Pluggy: https://github.com/pytest-dev/pluggy
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
