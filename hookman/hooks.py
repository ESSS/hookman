import ctypes
import inspect
from pathlib import Path
from typing import Callable, List

from hookman import hookman_utils


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
        # self._find_config_files(plugin_dirs)
        # else:
        #     raise FileNotFoundError("The given path doesn't have a .yaml file")

        self.hooks_available = {
            f'{hook.__name__.lower()}': f'{specs.project_name.lower()}_v{specs.version}_{hook.__name__.lower()}'
            for hook in specs.hooks
        }


    def get_hook_caller(self) -> 'HookCaller':
        """
        Return a HookCaller class that holds all references for the functions implemented on the plugins.
        """
        _hookman = __import__(self.specs.pyd_name)
        hook_caller = _hookman.HookCaller()

        plugin_config_files = hookman_utils.find_config_files(self.plugins_dirs)

        shared_libs_location = hookman_utils.get_shared_libs_path(plugin_config_files)

        for lib_path in shared_libs_location:
            self._bind_libs_functions_on_hook_caller(lib_path, hook_caller)

        return hook_caller


    def _bind_libs_functions_on_hook_caller(self, shared_lib_path: Path, hook_caller: 'HookCaller'):
        """
        Load the shared_lib_path from the plugin and bind methods that are implemented on the hook_caller
        """
        plugin_dll = ctypes.cdll.LoadLibrary(str(shared_lib_path))

        hooks_to_bind = {
            f'set_{hook_name}_function': hookman_utils.get_function_address(plugin_dll, full_hook_name)
            for hook_name, full_hook_name in self.hooks_available.items()
            if hookman_utils.is_implemented_on_plugin(plugin_dll, full_hook_name)
        }

        for hook in hooks_to_bind:
            cpp_func = getattr(hook_caller, hook)
            cpp_func(hooks_to_bind[hook])
