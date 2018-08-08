class HookmanError(Exception):
    """
    Base class for all hookman exceptions.
    """


class SharedLibraryNotFoundError(HookmanError):
    """
    Exception raise when the file informed doesn't contain a correct shared library
    Ex.: The user informed a linux plugin on a Windows application.
    """


class InvalidDestinationPathError(HookmanError):
    """
    Exception raised when the destination path to install the plugin is not one of the paths used
    by HookMan to find plugins already installed.
    """


class PluginAlreadyInstalledError(HookmanError):
    """
    Exception raise when a folder with the same name of the plugin already is placed on
    the destination folder informed.
    """


class ConflictBetweenPluginsError(HookmanError):
    """
    Exception raised when one or more plugins implements the same hook.
    """


class AssetsDirNotFoundError(HookmanError):
    """
    Exception raised when the assets folder it's not found on the root of the plugin folder
    """


class ArtifactsDirNotFoundError(HookmanError):
    """
    Exception raised when the artifacts folder it's not found on the root of the plugin folder
    """
