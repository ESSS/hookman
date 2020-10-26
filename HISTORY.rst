=======
History
=======

0.4.0 (2020-10-23)
==================

- When removing plugins they are first moved to a ``.trash`` dir and not directly deleted.
- Allow HookManager to call hooks of a specific plugin


0.3.0 (2019-12-16)
==================

- Rename the parameter ``dst_path`` to ``dest_path`` on ``install_plugin`` method.
- ``install_plugin`` now returns the name of the plugin when the installation is successful.
- Now the library path dir is added to ``PATH`` environment variable before load the library (Only on Windows).
- Added an optional "extras" entry to plugin definition yaml:

  - "extras" is a dictionary for adding (key, value) customized options, accessible in ``PluginInfo.extras``;
  - Plugin generation accepts a dict of default (key, value) pairs to be added to ``extras``;


0.2.0 (2019-02-08)
==================

- Moved load hook function code to ``HookCaller.load_impls_from_library`` function implemented in C++. This
  enables using hook functionality in projects which don't use Python as their entry point.

- ``HookSpecs`` now accepts an ``extra_includes`` argument, which can be used to add custom ``#include`` directives
  to the generated ``HookCaller.hpp`` file.

- ``HookCaller`` now contains a ``std::vector`` of functions bound to plugin implementations. This allows multiple
  plugins to implement the same hook; how the results of each call is to behave is responsibility of the caller.

  Because of this, the following classes/methods have been removed because they are no longer relevant:

  * ``ConflictBetweenPluginsError``
  * ``ConflictStatus``
  * ``HookMan.ensure_is_valid``
  * ``HookMan.get_status``


- Generated files now sport a "do not modify" comment header.

- Generation of the bindings code for ``HookCaller`` is skipped if ``specs.pyd_name`` is not defined.

- Code generation is now available directly in the command-line through the commands:

  * ``python -m hookman generate-plugin-template``
  * ``python -m hookman generate-project-files``
  * ``python -m hookman generate-hook-specs-h``
  * ``python -m hookman package-plugin``

- Explicitly declare ``extern "C"`` calling convention in the ``hook_specs.h`` file.

- The ``INIT_HOOKS`` macro has been removed as it didn't have any useful function.

0.1.7 (2018-08-23)
==================

- First Release on PyPI.

0.1.6 (2018-08-23)
==================

- Never released, deployment error.

0.1.5 (2018-08-23)
==================

- Never released, deployment error.


0.1.4 (2018-08-23)
==================

- Never released, deployment error.

0.1.3 (2018-08-23)
==================

- Never released, deployment error.


0.1.2 (2018-08-23)
==================

- Never released, deployment error.


0.1.1 (2018-08-23)
==================

- Never released, deployment error.
- Dropping bumperversion and using setuptool_scm

0.1.0 (2018-08-23)
==================

- Never released, deployment error.
