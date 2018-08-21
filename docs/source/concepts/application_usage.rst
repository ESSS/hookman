Application utilities
=====================

``HookMan`` offers a few utilities to help with the task to manage and handle plugins used by the application.


Install Plugin
---------------

The method ``Install Plugin`` requires two arguments:

1) The Path for the ``.hmplugin`` 
2) The destination to where the plugin should be placed.

This methods do the following checks:

- The destination Path should be one of the paths informed during the initialization of HookMan (plugins_dirs field).
- The plugins_dirs cannot have two plugins with the same name.


Plugins Available
------------------

With the method ``Plugins Available`` it's possible to check which Plugins are present on ``plugins_dirs``

This method returns a list of :ref:`plugin-info-api-section` with all plugins that are available on the plugins_dirs.

Basically the :ref:`plugin-info-api-section` contains an OrderedDict with the content of the config file with additional members.

- author
- description
- email
- hooks_implemented
- name
- shared_lib_name
- shared_lib_path
- version

Remove Plugin
--------------

This method receives the name of the plugin as input, and will remove completely the plugin from ``plugin_dirs``.


GetStatus
---------

With this method is possible to check if the plugins have conflicts between them.

If a conflict is found a list of ConflictStatus object will be returned, otherwise an empty list is returned.

.. Note:
    The ``get_status`` method currently just checks if more than on plugin implements the same hook.
    




