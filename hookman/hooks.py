import ctypes
import inspect
import os
import shutil
from pathlib import Path
from typing import Callable, List, Optional
from zipfile import ZipFile, is_zipfile

from hookman import hookman_utils
from hookman.exceptions import (
    InvalidDestinationPathError, InvalidZipFileError, PluginAlreadyInstalledError)
from hookman.plugin_config import PluginInfo


class HooksSpecs:
    """
    A class that holds the specification of the hooks, currently the following specification are available:
    - Project Name:
        This field will be used to identify the project and to name the hook functions
    - Version:
        The current version of the spec, when a new hook is created or modified this version should be incremented
    - Hooks:
        A list with the hooks available for the project, each hook is represented by a python function
    """

    def __init__(self, *, project_name: str, version: str, pyd_name: str,
            hooks: List[Callable]) -> None:
        for hook in hooks:
            self._check_hook_arguments(hook)
        self.project_name = project_name
        self.version = version
        self.pyd_name = pyd_name
        self.hooks = hooks

    def _check_hook_arguments(self, hook: Callable):
        """
        Check if the arguments of the hooks are valid.
        If an error is found, a TypeError exception will be raised
        """
        hook_args = inspect.getfullargspec(hook)

        if not hook_args.args:
            raise TypeError("It's not possible to create a hook without argument")

        annotate_args = {
            arg: hook_args.annotations[arg]
            for arg in hook_args.annotations
            if arg != 'return'
        }

        if len(annotate_args) != len(hook_args.args):
            raise TypeError("All hooks arguments must have the type informed")

        if not inspect.getdoc(hook):
            raise TypeError("All hooks must have documentation")


class HookMan:
    """
    Main class of HookMan, this class holds all the information related to the plugins
    """

    def __init__(self, *, specs: HooksSpecs, plugin_dirs: List[Path]):
        self.specs = specs
        self.plugins_dirs = plugin_dirs
        self.hooks_available = {
            f'{hook.__name__.lower()}': f'{specs.project_name.lower()}_v{specs.version}_{hook.__name__.lower()}'
            for hook in specs.hooks
        }

    def install_plugin(self, plugin_file_path: Path, dst_path: Path):
        """
        Extract the content of the zip file into plugin_dirs
        """
        plugin_file_zip = ZipFile(plugin_file_path)
        PluginInfo.plugin_file_validation(plugin_file_zip=plugin_file_zip)

        if dst_path not in self.plugins_dirs:
            raise InvalidDestinationPathError(f"Invalid destination path, {dst_path} is not one of "
                                              f"the paths that were informed when the HookMan "
                                              f"object was initialized: {self.plugins_dirs}.")

        plugin_name = Path(plugin_file_zip.filename).resolve().stem
        plugins_dirs = [x for x in dst_path.iterdir() if x.is_dir()]

        if plugin_name in [x.name for x in plugins_dirs]:
            raise PluginAlreadyInstalledError("Plugin already installed")

        plugin_destination_folder = dst_path / plugin_name
        plugin_destination_folder.mkdir(parents=True)
        plugin_file_zip.extractall(plugin_destination_folder)

    def remove_plugin(self, plugin_name: str):
        for plugin in self.plugins_available():
            if plugin.name == plugin_name:
                shutil.rmtree(plugin.location.parent)
                break


    def plugins_available(self) -> Optional[List[PluginInfo]]:
        """
        Return a list with all plugins that are available on the plugins_dirs.
        The list contains a PluginInfo object that contains information about the plugin
        (configuration available at the YAML file and computed values )
        """
        plugins_available = []
        plugin_config_files = hookman_utils.find_config_files(self.plugins_dirs)
        if plugin_config_files:
            for config_file in plugin_config_files:
                plugins_available.append(PluginInfo(config_file))

        return plugins_available

    def get_hook_caller(self):
        """
        Return a HookCaller class that holds all references for the functions implemented on the plugins.
        """
        _hookman = __import__(self.specs.pyd_name)
        hook_caller = _hookman.HookCaller()
        for plugin in self.plugins_available():
            self._bind_libs_functions_on_hook_caller(plugin.shared_lib_path, hook_caller)

        return hook_caller

    def _bind_libs_functions_on_hook_caller(self, shared_lib_path: Path, hook_caller):
        """
        Load the shared_lib_path from the plugin and bind methods that are implemented on the hook_caller
        """
        plugin_dll = ctypes.cdll.LoadLibrary(str(shared_lib_path))

        hooks_to_bind = {
            f'set_{hook_name}_function': PluginInfo.get_function_address(plugin_dll, full_hook_name)
            for hook_name, full_hook_name in self.hooks_available.items()
            if PluginInfo.is_implemented_on_plugin(plugin_dll, full_hook_name)
        }

        for hook in hooks_to_bind:
            cpp_func = getattr(hook_caller, hook)
            cpp_func(hooks_to_bind[hook])
