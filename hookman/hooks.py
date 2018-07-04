import ctypes
import inspect
import os
from pathlib import Path
from typing import Callable, List

import strictyaml


class HooksSpecs():
    """
    A class that holds the specification of the hooks, currently the following specification are available:
    - Project Name:
        This field will be used to identify the project and to name the hook functions
    - Version:
        The current version of the spec, when a new hook is created or modified this version should be incremented
    - Hooks:
        A list with the hooks available for the project, each hook is represented by a python function
    """

    def __init__(self, *, project_name: str, version: str, pyd_name: str, hooks: List[Callable]) -> None:
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


class HookMan():
    """
    Main class of HookMan, this class holds all the information related to the plugins
    """

    def __init__(self, *, specs: HooksSpecs, plugin_dirs: List[Path]):
        self.specs = specs

        config_files = []
        for plugin_dir in plugin_dirs:
            config_files += plugin_dir.glob('**/plugin.yaml')

        if config_files:
            self.plugin_config_files = config_files
        else:
            raise FileNotFoundError("The given path doesn't have a .yaml file")

        self.hooks_available = {
            f'{hook.__name__.lower()}': f'{specs.project_name}_v{specs.version}_{hook.__name__.lower()}'
            for hook in specs.hooks
        }

    def get_hook_caller(self) -> 'HookCaller':
        """
        Return a HookCaller class that holds all references for the functions implemented on the plugins.
        """
        _hookman = __import__(self.specs.pyd_name)
        hook_caller = _hookman.HookCaller()

        dll_path_locations = self._get_dll_locations()
        for dll_path in dll_path_locations:
            self._bind_dll_functions_on_hook_caller(dll_path, hook_caller)

        return hook_caller

    def _get_dll_locations(self) -> List[Path]:
        """
        Load the config file of each plugin available and return a list with the location of all DLL.
        """
        schema = strictyaml.Map({
            "author": strictyaml.Str(),
            "contact_information": strictyaml.Str(),
            "plugin_version": strictyaml.Str(),
            "dll_name": strictyaml.Str(),
            "lib_name": strictyaml.Str(),
        })

        dll_locations = []
        for hook_config_file in self.plugin_config_files:
            plugin_config_content = strictyaml.load(hook_config_file.read_text(), schema).data
            if os.sys.platform == 'win32':
                dll_name = plugin_config_content['dll_name']
            else:
                dll_name = plugin_config_content['lib_name']
            dll_locations.append(hook_config_file.parent / dll_name)

        return dll_locations

    def _bind_dll_functions_on_hook_caller(self, dll_path: Path, hook_caller : 'HookCaller'):
        """
        Load the dll_path from the plugin and bind methods that are implemented on the hook_caller
        """
        print(dll_path)
        plugin_dll = ctypes.cdll.LoadLibrary(str(dll_path))

        hooks_to_bind = {
            f'set_{hook_name}_function': self._get_function_addres(plugin_dll, full_hook_name)
            for hook_name, full_hook_name in self.hooks_available.items()
            if self.is_implemented_on_plugin(plugin_dll, full_hook_name)
        }

        for hook in hooks_to_bind:
            cpp_func = getattr(hook_caller, hook)
            cpp_func(hooks_to_bind[hook])

    def _get_function_addres(self, plugin_dll: ctypes.CDLL, hook_name: str) -> int:
        """
        Return the address of the requested hook for the given plugin_dll.

        Obs.: The hook_name should be the full name of the hook
        Ex.: {project}_{version}_{hook_name} -> hookman_v4_friction_factor
        """
        return ctypes.cast(getattr(plugin_dll, hook_name), ctypes.c_void_p).value

    def is_implemented_on_plugin(self, plugin_dll: ctypes.CDLL, hook_name: str) -> bool:
        """
        Check if the given function name is available on the plugin_dll informed

        Obs.: The hook_name should be the full name of the hook
        Ex.: {project}_{version}_{hook_name} -> hookman_v4_friction_factor
        """
        try:
            getattr(plugin_dll, hook_name)
        except AttributeError:
            return False

        return True
