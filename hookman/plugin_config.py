import ctypes
import sys
from pathlib import Path
from typing import List
from zipfile import ZipFile

import attr
from attr import attrib

from hookman.exceptions import SharedLibraryNotFoundError
from hookman.hookman_utils import load_shared_lib

from strictyaml import Map, MapPattern, Optional, Str

PLUGIN_CONFIG_SCHEMA = Map(
    {
        "caption": Str(),
        "version": Str(),
        "author": Str(),
        "email": Str(),
        "id": Str(),
        Optional("extras"): MapPattern(Str(), Str()),
    }
)


@attr.s
class PluginInfo(object):
    """
    Class that holds all information related to the plugin with some auxiliary methods
    """

    yaml_location = attrib(type=Path)
    hooks_available = attrib(validator=attr.validators.optional(attr.validators.instance_of(dict)))

    author = attrib(type=str, init=False)
    description = attrib(type=str, default="Could not find a description", init=False)
    email = attrib(type=str, init=False)
    hooks_implemented = attrib(type=list, init=False)
    caption = attrib(type=str, init=False)
    shared_lib_name = attrib(type=str, init=False)
    shared_lib_path = attrib(type=Path, init=False)
    version = attrib(type=str, init=False)
    extras = attrib(attr.Factory(dict), init=False)

    def __attrs_post_init__(self):
        plugin_config_file_content = self._load_yaml_file(
            self.yaml_location.read_text(encoding="utf-8")
        )

        name = plugin_config_file_content["id"]
        shared_lib_name = f"{name}.dll" if sys.platform == "win32" else f"lib{name}.so"

        object.__setattr__(self, "shared_lib_name", shared_lib_name)
        object.__setattr__(
            self, "shared_lib_path", self.yaml_location.parents[1] / "artifacts" / shared_lib_name
        )

        object.__setattr__(self, "author", plugin_config_file_content["author"])
        object.__setattr__(self, "caption", plugin_config_file_content["caption"])
        object.__setattr__(self, "email", plugin_config_file_content["email"])
        object.__setattr__(self, "version", plugin_config_file_content["version"])
        object.__setattr__(self, "extras", plugin_config_file_content.get("extras", {}))

        # The id bellow guarantee to me that the plugin_id to be used in the application was not changed by a config file.
        object.__setattr__(
            self, "id", self._get_plugin_id_from_dll(plugin_config_file_content["id"])
        )

        if not self.hooks_available is None:
            object.__setattr__(self, "hooks_implemented", self._get_hooks_implemented())

        readme_file = self.yaml_location.parent / "README.md"
        if readme_file.exists():
            object.__setattr__(self, "description", readme_file.read_text())

    def _check_if_shared_lib_exists(self):
        if not self.shared_lib_path.is_file():
            raise SharedLibraryNotFoundError(
                f"{self.shared_lib_name} could not be found in {self.shared_lib_path.parent}"
            )

    def _get_plugin_id_from_dll(self, plugin_id_from_plugin_yaml: str) -> str:
        self._check_if_shared_lib_exists()
        with load_shared_lib(str(self.shared_lib_path)) as plugin_dll:
            plugin_dll.get_plugin_id.restype = ctypes.c_char_p
            plugin_id_from_shared_lib = plugin_dll.get_plugin_id().decode("utf-8")
            if plugin_id_from_shared_lib != plugin_id_from_plugin_yaml:
                msg = (
                    f'Error, the plugin_id inside plugin.yaml is "{plugin_id_from_plugin_yaml}" '
                    f"while the plugin_id inside the {self.shared_lib_name} is {plugin_id_from_shared_lib}"
                )
                raise RuntimeError(msg)
            return plugin_id_from_shared_lib

    def _get_hooks_implemented(self) -> List[str]:
        """
        Return a list of which hooks from "hooks_available" the shared library implements
        """
        self._check_if_shared_lib_exists()
        with load_shared_lib(str(self.shared_lib_path)) as plugin_dll:
            hooks_implemented = [
                hook_name
                for hook_name, full_hook_name in self.hooks_available.items()
                if PluginInfo.is_implemented_on_plugin(plugin_dll, full_hook_name)
            ]
        return hooks_implemented

    @classmethod
    def is_implemented_on_plugin(cls, plugin_dll: ctypes.CDLL, hook_name: str) -> bool:
        """
        Check if the given function name is available on the plugin_dll informed

        .. note:: The hook_name should be the full name of the hook
        Ex.: {project}_{version}_{hook_name} -> hookman_v4_friction_factor
        """
        try:
            getattr(plugin_dll, hook_name)
        except AttributeError:
            return False

        return True

    @classmethod
    def _load_yaml_file(cls, yaml_content):
        import strictyaml

        plugin_config_file_content = strictyaml.load(yaml_content, PLUGIN_CONFIG_SCHEMA).data
        if sys.platform == "win32":
            plugin_config_file_content[
                "shared_lib_name"
            ] = f"{plugin_config_file_content['id']}.dll"
        else:
            plugin_config_file_content[
                "shared_lib_name"
            ] = f"lib{plugin_config_file_content['id']}.so"
        return plugin_config_file_content

    @classmethod
    def validate_plugin_file(cls, plugin_file_zip: ZipFile):
        """
        Check if the given plugin_file is valid,
        currently the only check that this method do is to verify if the id is available
        """
        list_of_files = [file.filename for file in plugin_file_zip.filelist]

        plugin_file_str = plugin_file_zip.read("assets/plugin.yaml").decode("utf-8")
        plugin_file_content = PluginInfo._load_yaml_file(plugin_file_str)

        if not any(plugin_file_content["shared_lib_name"] in file for file in list_of_files):
            raise SharedLibraryNotFoundError(
                f"{plugin_file_content['shared_lib_name']} could not be found inside the plugin file"
            )
