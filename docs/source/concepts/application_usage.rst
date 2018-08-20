Integration with your application
=================================

Install Plugin:
Extract the content of the zip file into the same directory informed on the __init__ from Hookman

Plugins available:
Return a list with all plugins that are available on the plugins_dirs.
The list contains a OrderedDict with the content of the config file:
- plugin_name
- plugin_version
- author
- email
- shared_lib
- description

Remove Plugin:
Remove completey the plugin from plugin_dirs, by giving the plugins name


This pull request implements the method GetStatus which will evaluate the plugins already installed and checks if there isn't conflict between them.

Notice that this method just checks if more than on plugin implements the same hook.

If a conflict is found, a ConflictStatus object will be returned, this object contains the name of the hook that has multiple implementations and the name of these plugins.


