import ctypes
import os
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional, Union


def load_plugin_config_file(hook_config_file: str) -> OrderedDict:
    """
    Load the content of the plugin.yaml file.
    Noticed that the entry shared_lib will be update according to the operating system

    Obs.: This method receives a str instead of Path because when the ZipFile is loaded (on install_plugin)
    it's not possible to get a Path, just the file content.
    """
    import strictyaml
    schema = strictyaml.Map({
        "plugin_name": strictyaml.Str(),
        "plugin_version": strictyaml.Str(),
        "author": strictyaml.Str(),
        "email": strictyaml.Str(),
        "shared_lib": strictyaml.Str(),
    })
    hook_config_file_content = strictyaml.load(hook_config_file, schema).data

    if os.sys.platform == 'win32':
        hook_config_file_content['shared_lib'] = f"{hook_config_file_content['shared_lib']}.dll"
    else:
        hook_config_file_content['shared_lib'] = f"lib{hook_config_file_content['shared_lib']}.so"

    return hook_config_file_content


def find_config_files(plugin_dirs: Union[List[Path], Path]) -> List[Path]:
    """
    Try to find all configurations files from plugins implementations on the given path (plugins_dirs)
    If in the given there is any plugin, this function will return None
    """
    config_files = []

    if not isinstance(plugin_dirs, list):
        plugin_dirs = [plugin_dirs]

    for plugin_dir in plugin_dirs:
        config_files += plugin_dir.glob('**/plugin.yaml')

    config_files.sort()
    return config_files


def get_shared_libs_path(plugin_config_files: Union[List[Path], Path]) -> Optional[List[Path]]:
    """
    Load the config file of each plugin available and return a list with the location of all DLL.
    If a given config files doesn't exist a FileNotFoundError exception will be raised.
    """
    shared_lib_paths = []

    if not isinstance(plugin_config_files, list):
        plugin_config_files = [plugin_config_files]  # type: List[Path]

    for hook_config_file in plugin_config_files:
        if not hook_config_file.exists():
            continue

        plugin_config_content = load_plugin_config_file(hook_config_file.read_text())
        shared_lib_paths.append(hook_config_file.parent / plugin_config_content['shared_lib'])

    return shared_lib_paths


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
