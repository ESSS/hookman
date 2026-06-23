import inspect
import logging
import shutil
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from packaging.version import Version
from pluggy import HookCaller

from hookman import hookman_utils
from hookman.exceptions import InvalidDestinationPathError
from hookman.exceptions import PluginAlreadyInstalledError
from hookman.exceptions import SharedLibraryLoadError
from hookman.exceptions import SharedLibraryNotFoundError
from hookman.hookman_utils import change_path_env
from hookman.plugin_config import PluginInfo

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InstalledPluginInfo:
    """
    Responsible to store the information about an installed plugin.
    """

    id: str
    version: Version


@dataclass(frozen=True)
class PluginLoadFailure:
    """Information about a plugin that was found but failed to load during discovery."""

    yaml_location: Path
    """Path to the plugin's plugin.yaml file."""

    plugin_id: str
    """The plugin id, read from the plugin's YAML config file."""

    reason: str
    """Human-readable description of why the plugin failed to load."""


class HookSpecs:
    """
    A class that holds the specification of the hooks, currently the following specification are available:

    :kwparam project_name:
        This field will be used to identify the project and to name the hook functions. This is usually a project name
        in a user-friendly format, such as "My Project".

    :kwparam str version:
        The current version of the spec, when a new hook is created or modified this version should be changed.

    :kwparam str pyd_name:
        Base name of the shared library for the bindings for the HookCaller class. If None, no bindings will be
        generated.

    :kwparam List[function] hooks:
        A list with the hooks available for the project, each hook is a python function with type annotations.

    :kwparam List[str] extra_includes:
        Extra #include directives that will be added to the generated HookCaller.hpp file.
    """

    def __init__(
        self,
        *,
        project_name: str,
        version: str,
        pyd_name: str | None = None,
        hooks: Sequence[Callable],
        extra_includes: Sequence[str] = (),
    ) -> None:
        for hook in hooks:
            self._check_hook_arguments(hook)
        self.project_name = project_name
        self.version = version
        self.pyd_name = pyd_name
        self.hooks = hooks
        self.extra_includes = list(extra_includes)

    def _check_hook_arguments(self, hook: Callable) -> None:
        """
        Check if the arguments of the hooks are valid.
        If an error is found, a TypeError exception will be raised
        """
        hook_args = inspect.getfullargspec(hook)

        if not hook_args.args:
            raise TypeError("It's not possible to create a hook without argument")

        annotate_args = {
            arg: hook_args.annotations[arg] for arg in hook_args.annotations if arg != "return"
        }

        if len(annotate_args) != len(hook_args.args):
            raise TypeError("All hooks arguments must have the type informed")

        if not inspect.getdoc(hook):
            raise TypeError("All hooks must have documentation")


class HookMan:
    """
    Main class of HookMan, this class holds all the information related to the plugins
    """

    _TRASH_DIR_NAME = ".trash"

    def __init__(self, *, specs: HookSpecs, plugin_dirs: Sequence[Path]) -> None:
        self.specs = specs
        self.plugins_dirs = plugin_dirs
        self.hooks_available = {
            f"{hook.__name__.lower()}": f"{specs.project_name.lower()}_v{specs.version}_{hook.__name__.lower()}"
            for hook in specs.hooks
        }

    def install_plugin(self, plugin_file_path: Path, dest_path: Path) -> InstalledPluginInfo:
        """
        Extract the content of the zip file into dest_path.
        If the installation occurs successfully a InstalledPluginInfo will be returned.

        The following checks will be executed to validate the consistency of the inputs:

            1. The destination Path should be one of the paths informed during the initialization of HookMan (plugins_dirs field).

            2. The plugins_dirs cannot have two plugins with the same name and version.

        :param: plugin_file_path:
            The Path for the ``.hmplugin``

        :param dest_path:
            The destination to where the plugin should be placed.
        """
        plugin_file_zip = ZipFile(plugin_file_path)
        PluginInfo.validate_plugin_file(plugin_file_zip=plugin_file_zip)

        if dest_path not in self.plugins_dirs:
            raise InvalidDestinationPathError(
                f"Invalid destination path, {dest_path} is not one of "
                f"the paths that were informed when the HookMan "
                f"object was initialized: {self.plugins_dirs}."
            )

        yaml_content = plugin_file_zip.open("assets/plugin.yaml").read().decode("utf-8")

        yaml_data = PluginInfo._load_yaml_file(yaml_content)
        plugin_id: str = yaml_data["id"]
        plugin_version: str = yaml_data["version"]
        plugin_id_version = f"{plugin_id}-{plugin_version}"

        plugins_dirs = [x for x in dest_path.iterdir() if x.is_dir()]

        if plugin_id_version in [x.name for x in plugins_dirs]:
            raise PluginAlreadyInstalledError("Plugin already installed")

        plugin_destination_folder = dest_path / plugin_id_version
        plugin_destination_folder.mkdir(parents=True)
        plugin_file_zip.extractall(plugin_destination_folder)
        return InstalledPluginInfo(version=Version(plugin_version), id=plugin_id)

    def _move_to_trash(self, root_dir: Path, name: str) -> None:
        """
        Move the folder named ``name`` to a trash sub folder in the same ``root_dir``.

        :root_dir: The folder containing ``name`` to be moved to the trash.
        :name: The name of the folder to be moved.
        """
        import os
        import tempfile

        trash_dir = root_dir / self._TRASH_DIR_NAME
        trash_dir.mkdir(parents=True, exist_ok=True)
        src_dir = root_dir / name
        dst_dir = tempfile.mkdtemp(dir=trash_dir)
        dst_dir = os.path.join(dst_dir, name)
        src_dir.rename(dst_dir)

    def _try_clear_trash(self, root_dir: Path) -> None:
        """
        Clear the trash sub folder from ``root_dir``.
        """
        from contextlib import suppress

        trash_dir = root_dir / self._TRASH_DIR_NAME
        for filename in trash_dir.glob("*"):
            if filename.is_dir():
                shutil.rmtree(filename, ignore_errors=True)
            else:
                with suppress(OSError):
                    filename.unlink()

    def remove_plugin(self, caption: str, version: Version | None = None) -> None:
        """
        This method receives the name and version of plugin as input, and will remove completely the
        plugin from ``plugin_dirs``.

        :param caption:
            Name of the plugin to be removed.

        :param version:
            Optional parameter used to remove a specific version of plugin. Case it is not specified,
            all versions of a given plugin will be removed.
        """
        for plugin in self.get_plugins_available():
            plugin_dir = plugin.yaml_location.parents[1]
            root_dir = plugin_dir.parent
            remove_plugin = False

            if version is None and caption in plugin_dir.name:
                remove_plugin = True
            elif plugin.id == caption and version == plugin.version:
                remove_plugin = True

            if remove_plugin:
                self._move_to_trash(root_dir, plugin_dir.name)
                self._try_clear_trash(root_dir)
                break

    def get_plugins_available_and_failures(
        self, ignored_plugins: Sequence[str] = ()
    ) -> tuple[list[PluginInfo], list[PluginLoadFailure]]:
        """
        Return all plugins that loaded successfully, plus a list of those that failed.

        A single incompatible plugin DLL will not abort discovery of the remaining
        plugins — `SharedLibraryLoadError` is caught per-plugin and reported in the
        failures list instead.

        Optionally you can pass a list of plugin ids to exclude from both lists.

        :returns:
            A tuple of (successful `PluginInfo` list, `PluginLoadFailure` list).
        """
        plugin_ids_and_files = [
            (plugin_id, f)
            for f in hookman_utils.find_config_files(
                self.plugins_dirs, ignored_sub_dir_names=[self._TRASH_DIR_NAME]
            )
            if (plugin_id := PluginInfo.parse_id(f)) not in ignored_plugins
        ]

        plugins: list[PluginInfo] = []
        failures: list[PluginLoadFailure] = []
        for plugin_id, plugin_file in plugin_ids_and_files:
            try:
                plugin_info = PluginInfo(plugin_file, self.hooks_available)
            except (SharedLibraryLoadError, SharedLibraryNotFoundError) as error:
                reason = str(error)
                _logger.warning("Plugin at '%s' failed to load: %s", plugin_file, reason)
                failures.append(
                    PluginLoadFailure(
                        yaml_location=plugin_file,
                        plugin_id=plugin_id,
                        reason=reason,
                    )
                )
                continue
            else:
                plugins.append(plugin_info)
        return plugins, failures

    def get_plugins_available(self, ignored_plugins: Sequence[str] = ()) -> Sequence[PluginInfo]:
        """
        Return a list of :ref:`plugin-info-api-section` that are available on ``plugins_dirs``

        Optionally you can pass a list of plugins that should be ignored.
        When informed, the `ignored_plugins` must be a list with the names of the plugins (same as shared_lib_name)
        instead of the plugin caption.

        Plugins whose DLL fails to load are silently skipped with a warning logged.
        Use `get_plugins_available_and_failures` to receive the failure details.
        """
        plugins, _failures = self.get_plugins_available_and_failures(ignored_plugins)
        return plugins

    def get_hook_caller(self, ignored_plugins: Sequence[str] = ()) -> HookCaller:
        """
        Return a HookCaller class that holds all references for the functions implemented
        on the plugins.

        When informed, the `ignored_plugins` must be a list with the names of the plugins (same as shared_lib_name)
        instead of the plugin caption.

        Plugins whose DLL fails to load are silently skipped with a warning logged — they
        do not raise an exception here. Use `get_plugins_available_and_failures` to
        inspect load failures.
        """
        assert self.specs.pyd_name is not None, f"Specs {self.specs!r}.pyd_name must be set"
        _hookman = __import__(self.specs.pyd_name)
        hook_caller = _hookman.HookCaller()
        for plugin in self.get_plugins_available(ignored_plugins):
            with change_path_env(str(plugin.shared_lib_path)):
                hook_caller.load_impls_from_library(str(plugin.shared_lib_path), plugin.id)
        return hook_caller
