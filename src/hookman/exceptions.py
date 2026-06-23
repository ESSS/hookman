from pathlib import Path


class HookmanError(Exception):
    """
    Base class for all hookman exceptions.
    """


class SharedLibraryNotFoundError(HookmanError):
    """
    Exception raise when the file informed doesn't contain a correct shared library
    Ex.: The user informed a linux plugin on a Windows application.
    """


class SharedLibraryLoadError(HookmanError):
    """
    Exception raised when a shared library exists but fails to load.

    This typically occurs when the plugin DLL has unresolved imports or
    incompatible entry points — for example, when a plugin bundles a
    conflicting version of a dependency that the host also provides.

    :param shared_lib_path: Path to the shared library that failed to load.
    :param reason: Human-readable OS error description.
    """

    def __init__(self, shared_lib_path: Path, reason: str) -> None:
        self.shared_lib_path = shared_lib_path
        self.reason = reason
        super().__init__(f"Failed to load '{shared_lib_path}': {reason}")


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


class AssetsDirNotFoundError(HookmanError):
    """
    Exception raised when the assets folder it's not found on the root of the plugin folder
    """


class ArtifactsDirNotFoundError(HookmanError):
    """
    Exception raised when the artifacts folder it's not found on the root of the plugin folder
    """
