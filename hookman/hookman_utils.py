import ctypes
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import List, Union


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

    return config_files


@contextmanager
def load_shared_lib(shared_lib_path: str) -> ctypes.CDLL:
    """
    Load a shared library using ctypes freeing the resource at end.
    """
    plugin_dll = ctypes.cdll.LoadLibrary(shared_lib_path)
    try:
        yield plugin_dll
    finally:
        if sys.platform == 'win32':
            from _ctypes import FreeLibrary
            FreeLibrary(plugin_dll._handle)
        else:
            from _ctypes import dlclose
            dlclose(plugin_dll._handle)
