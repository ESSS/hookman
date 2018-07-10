import ctypes
import os
from collections import OrderedDict
from typing import List, Optional, Union

from coilib50.path.dotpath import Path


def load_config_content(hook_config_file: Path) -> OrderedDict:
    import strictyaml
    schema = strictyaml.Map({
        "author": strictyaml.Str(),
        "contact_information": strictyaml.Str(),
        "plugin_version": strictyaml.Str(),
        "dll_name": strictyaml.Str(),
        "lib_name": strictyaml.Str(),
    })
    hook_config_file_content = strictyaml.load(hook_config_file.read_text(), schema).data
    return hook_config_file_content


def find_config_files(plugin_dirs: Union[List[Path], Path]) -> Optional[List[Path]]:
    """
    Try to find all configurations files from plugins implementations on the given path (plugins_dirs)
    If in the given there is any plugin, this function will return None
    """
    config_files = []

    if not isinstance(plugin_dirs, list):
        plugin_dirs = [plugin_dirs]

    for plugin_dir in plugin_dirs:
        config_files += plugin_dir.glob('**/plugin.yaml')

    return config_files


def get_shared_libs_path(plugin_config_files: Union[List[Path], Path]) -> Optional[List[Path]]:
    """
    Load the config file of each plugin available and return a list with the location of all DLL.
    If a given config files doesn't exist a FileNotFoundError exception will be raised.
    """

    dll_locations = []

    if not isinstance(plugin_config_files, list):
        plugin_config_files = [plugin_config_files]  # type: List[Path]

    for hook_config_file in plugin_config_files:
        if not hook_config_file.exists():
            continue

        plugin_config_content = load_config_content(hook_config_file)

        if os.sys.platform == 'win32':
            dll_name = plugin_config_content['dll_name']
        else:
            dll_name = plugin_config_content['lib_name']
        dll_locations.append(hook_config_file.parent / dll_name)

    return dll_locations


def is_implemented_on_plugin(plugin_dll: ctypes.CDLL, hook_name: str) -> bool:
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


def get_function_address(plugin_dll: ctypes.CDLL, hook_name: str) -> int:
    """
    Return the address of the requested hook for the given plugin_dll.

    Obs.: The hook_name should be the full name of the hook
    Ex.: {project}_{version}_{hook_name} -> hookman_v4_friction_factor
    """
    return ctypes.cast(getattr(plugin_dll, hook_name), ctypes.c_void_p).value
