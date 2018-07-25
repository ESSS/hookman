class HookmanError(Exception):
    """
    Base class for all hookman exceptions.
    """


class PluginNotFoundError(HookmanError):
    '''
    Exception raise when the file informed doesn't contain a correct shared library
    Ex.: The user informed a linux plugin on a Windows application.
    '''


class InvalidDestinationPathError(HookmanError):
    '''
    Exception raised when the destination path to install the plugin is not one of the paths used
    by HookMan to find plugins already installed
    '''


class PluginAlreadyInstalledError(HookmanError):
    '''
    Exception raise when a folder with the same name of the plugin already is placed on the destination folder informed
    '''
