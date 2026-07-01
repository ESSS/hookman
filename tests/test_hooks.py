# mypy: allow-untyped-defs
import dataclasses
import sys
from pathlib import Path

import pytest
from packaging.version import Version

from hookman.hooks import HookMan
from hookman.hooks import HookSpecs
from hookman.hooks import PluginInfo


def _get_plugin_id_set(plugin_info_list):
    """
    Return a set with the ids from plugin info list.
    """
    return {plugin_info.id for plugin_info in plugin_info_list}


def _get_names_inside_folder(folder):
    """
    Return a set with the names of the elements inside a folder.
    """
    return {file.name for file in folder.iterdir()}


def test_hook_specs_without_arguments() -> None:
    def method_without_arguments() -> "float":
        """
        test_method_without_arguments
        """
        return 0.0

    # A hook must have parameters
    with pytest.raises(TypeError, match="It's not possible to create a hook without argument"):
        _specs = HookSpecs(
            project_name="acme", version="1", pyd_name="_acme", hooks=[method_without_arguments]
        )


def test_hook_specs_with_missing_type_on_argument() -> None:
    def method_with_missing_type_on_argument(a: "int", b) -> "float":
        """
        fail_method_with_missing_type_on_argument
        """
        return 0.0

    # All arguments of the hook must inform the type.
    with pytest.raises(TypeError, match="All hooks arguments must have the type informed"):
        _specs = HookSpecs(
            project_name="acme",
            version="1",
            pyd_name="_acme",
            hooks=[method_with_missing_type_on_argument],
        )


def test_hook_specs_without_docs_arguments() -> None:
    def method_with_docs_missing(a: "int") -> "int":
        return 0

    with pytest.raises(TypeError, match="All hooks must have documentation"):
        _specs = HookSpecs(
            project_name="acme", version="1", pyd_name="_acme", hooks=[method_with_docs_missing]
        )


def test_get_hook_caller_with_conflict(simple_plugin, simple_plugin_2) -> None:
    plugins_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugins_dirs)
    hc = hm.get_hook_caller()
    assert len(hc.friction_factor_impls()) == 2
    assert len(hc.env_temperature_impls()) == 1


def test_get_hook_caller(simple_plugin) -> None:
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[simple_plugin["path"]])
    hook_caller = hm.get_hook_caller()
    friction_factors = hook_caller.friction_factor_impls()
    env_temperatures = hook_caller.env_temperature_impls()
    assert len(friction_factors) == 1
    assert len(env_temperatures) == 0
    assert friction_factors[0](1, 2) == 3

    # Call a hook for a specific plugin implementation
    assert hook_caller.friction_factor_impl("simple_plugin")(1, 2) == 3


def test_get_hook_caller_passing_ignored_plugins(datadir, simple_plugin, simple_plugin_2) -> None:
    plugins_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugins_dirs)

    assert len(hm.get_plugins_available()) == 2
    assert len(list((datadir / "plugins").iterdir())) == 2

    hook_caller = hm.get_hook_caller(ignored_plugins=["simple_plugin_2"])
    env_temperatures = hook_caller.env_temperature_impls()

    # Plugin2 implements the Hook env_temperature
    assert len(env_temperatures) == 0


def test_get_hook_caller_without_plugin(datadir, simple_plugin) -> None:
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[datadir / "some_non_existing_folder"])
    hook_caller = hm.get_hook_caller()
    friction_factors = hook_caller.friction_factor_impls()
    env_temperatures = hook_caller.env_temperature_impls()
    assert len(friction_factors) == 0
    assert len(env_temperatures) == 0


def test_plugins_available_plain(simple_plugin, simple_plugin_2) -> None:
    plugin_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugin_dirs)
    plugins = hm.get_plugins_available()
    assert len(plugins) == 2

    assert list(dataclasses.asdict(plugins[0]).keys()) == [
        "yaml_location",
        "hooks_available",
        "description",
        "author",
        "email",
        "hooks_implemented",
        "caption",
        "shared_lib_name",
        "shared_lib_path",
        "version",
        "requirements",
        "extras",
        "id",
    ]

    plugins = hm.get_plugins_available(ignored_plugins=["simple_plugin_2"])
    assert len(plugins) == 1


def _make_broken_plugin_dir(root: Path) -> Path:
    """Create a plugin directory with a valid yaml but an unloadable shared library."""
    broken_plugin_dir = root / "broken_plugin-1.0.0"
    (broken_plugin_dir / "assets").mkdir(parents=True)
    (broken_plugin_dir / "assets" / "plugin.yaml").write_text(
        "caption: 'Broken Plugin'\nversion: '1.0.0'\nauthor: 'a'\nemail: 'a@a.com'\nid: 'broken_plugin'\n"
    )
    artifacts_dir = broken_plugin_dir / "artifacts"
    artifacts_dir.mkdir()
    lib_name = "broken_plugin.dll" if sys.platform == "win32" else "libbroken_plugin.so"
    (artifacts_dir / lib_name).write_text("not a real shared library")
    return broken_plugin_dir


def test_get_plugins_available_and_failures_with_broken_plugin(
    tmp_path, simple_plugin, acme_hook_specs
) -> None:
    """A plugin with an unloadable DLL appears in the failures list; valid plugins still load."""
    # Use a dedicated subdirectory so that pytest-datadir content written to tmp_path
    # by other fixtures (e.g. multiple_plugins without compiled .so files) is not
    # picked up by find_config_files' recursive glob.
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    broken_plugin_dir = _make_broken_plugin_dir(plugins_root)

    hm = HookMan(specs=acme_hook_specs, plugin_dirs=[simple_plugin["path"], plugins_root])
    plugins, failures = hm.get_plugins_available_and_failures()

    assert [p.id for p in plugins] == ["simple_plugin"]
    [failure] = failures
    assert failure.plugin_id == "broken_plugin"
    assert failure.yaml_location == broken_plugin_dir / "assets" / "plugin.yaml"
    assert failure.reason  # Non-empty OS-dependent error message.


def test_get_plugins_available_skips_failures(tmp_path, simple_plugin, acme_hook_specs) -> None:
    """get_plugins_available silently skips plugins that fail to load."""
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    _make_broken_plugin_dir(plugins_root)

    hm = HookMan(specs=acme_hook_specs, plugin_dirs=[simple_plugin["path"], plugins_root])
    plugins = hm.get_plugins_available()

    # The broken plugin is skipped; the valid one still loads.
    assert [p.id for p in plugins] == ["simple_plugin"]


def _make_missing_dll_plugin_dir(root: Path) -> Path:
    """Create a plugin directory with a valid YAML but no shared library file."""
    plugin_dir = root / "missing_dll_plugin-1.0.0"
    (plugin_dir / "assets").mkdir(parents=True)
    (plugin_dir / "assets" / "plugin.yaml").write_text(
        "caption: 'Missing DLL Plugin'\nversion: '1.0.0'\nauthor: 'a'\nemail: 'a@a.com'\nid: 'missing_dll_plugin'\n"
    )
    (plugin_dir / "artifacts").mkdir()
    return plugin_dir


def test_get_plugins_available_and_failures_with_missing_dll(tmp_path, acme_hook_specs) -> None:
    """A plugin whose DLL is absent (SharedLibraryNotFoundError) lands in the failures list."""
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    missing_plugin_dir = _make_missing_dll_plugin_dir(plugins_root)

    hm = HookMan(specs=acme_hook_specs, plugin_dirs=[plugins_root])
    plugins, failures = hm.get_plugins_available_and_failures()

    assert plugins == []
    [failure] = failures
    assert failure.plugin_id == "missing_dll_plugin"
    assert failure.yaml_location == missing_plugin_dir / "assets" / "plugin.yaml"
    assert failure.reason


def test_get_plugins_available_and_failures_ignored_plugin_excluded_from_failures(
    tmp_path, acme_hook_specs
) -> None:
    """An ignored plugin that also fails to load must not appear in failures."""
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    _make_broken_plugin_dir(plugins_root)

    hm = HookMan(specs=acme_hook_specs, plugin_dirs=[plugins_root])
    plugins, failures = hm.get_plugins_available_and_failures(ignored_plugins=["broken_plugin"])

    assert plugins == []
    assert failures == []


def test_plugins_available_ignore_trash(datadir, simple_plugin, simple_plugin_2) -> None:
    plugin_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugin_dirs)

    plugins = hm.get_plugins_available()
    assert {p.id for p in plugins} == {"simple_plugin", "simple_plugin_2"}

    hm._move_to_trash(datadir / "plugins", "simple_plugin-1.0.0")
    plugins = hm.get_plugins_available()
    assert {p.id for p in plugins} == {"simple_plugin_2"}

    hm._move_to_trash(datadir / "plugins", "simple_plugin_2-1.0.0")
    plugins = hm.get_plugins_available()
    assert {p.id for p in plugins} == set()


def test_try_clean_cache_ignore_os_errors(datadir, simple_plugin, monkeypatch) -> None:
    import sys

    # Windows has problems deleting filer/folders in used.
    win = sys.platform.startswith("win32")

    plugin_dir = datadir / "plugins"
    trash_folder = plugin_dir / ".trash"
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugin_dir)
    hm._move_to_trash(plugin_dir, "simple_plugin-1.0.0")
    (trash_item_dir,) = trash_folder.glob("*")
    # Change cwd to inside the trash item folder, windows will not be able to delete a directory
    # in use.
    monkeypatch.chdir(trash_item_dir)
    hm._try_clear_trash(plugin_dir)
    monkeypatch.chdir(datadir)
    assert trash_item_dir.exists() is win
    # With the folder not busy it can be removed.
    hm._try_clear_trash(plugin_dir)
    assert not trash_item_dir.exists()
    # Clear trash do not raise if some file is in use, will will not be able to delete a file
    # is use.
    some_trash_file = trash_folder / "some_trash_file"
    some_trash_file.write_text("foobar")
    with some_trash_file.open("w"):
        hm._try_clear_trash(plugin_dir)
    # File not in use is deleted.
    assert some_trash_file.exists() is win
    hm._try_clear_trash(plugin_dir)
    assert not some_trash_file.exists()


def test_install_plugin_without_lib(mocker, simple_plugin, plugins_zip_folder) -> None:
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[simple_plugin["path"]])

    mocked_config_content = {"shared_lib_name": "NON_VALID_SHARED_LIB"}
    mocker.patch.object(PluginInfo, "_load_yaml_file", return_value=mocked_config_content)

    # Trying to install without a SHARED LIB inside the plugin
    from hookman.exceptions import SharedLibraryNotFoundError

    with pytest.raises(
        SharedLibraryNotFoundError,
        match=f"{mocked_config_content['shared_lib_name']} could not be found inside the plugin file",
    ):
        hm.install_plugin(plugin_file_path=simple_plugin["zip"], dest_path=simple_plugin["path"])


def test_install_with_invalid_dest_path(simple_plugin) -> None:
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[simple_plugin["path"]])

    # Trying to install in the plugin on an different path informed on the construction of the HookMan object
    from hookman.exceptions import InvalidDestinationPathError

    with pytest.raises(InvalidDestinationPathError, match="Invalid destination path"):
        hm.install_plugin(
            plugin_file_path=simple_plugin["zip"], dest_path=simple_plugin["path"] / "INVALID_PATH"
        )


def test_install_plugin_duplicate(simple_plugin) -> None:
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[simple_plugin["path"].parent])
    import os

    os.makedirs(simple_plugin["path"] / "simple_plugin-1.0.0")

    # Trying to install the plugin in a folder that already has a folder with the same name and version of plugin.
    from hookman.exceptions import PluginAlreadyInstalledError

    with pytest.raises(PluginAlreadyInstalledError, match="Plugin already installed"):
        hm.install_plugin(
            plugin_file_path=simple_plugin["zip"], dest_path=simple_plugin["path"].parent
        )


def test_install_plugin(datadir, simple_plugin) -> None:
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[simple_plugin["path"]])
    assert (simple_plugin["path"] / "simple_plugin-1.0.0").exists() is False
    hm.install_plugin(plugin_file_path=simple_plugin["zip"], dest_path=simple_plugin["path"])
    assert (simple_plugin["path"] / "simple_plugin-1.0.0").exists() is True


def test_remove_plugin(datadir, simple_plugin, simple_plugin_2) -> None:
    plugins_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugins_dirs)

    assert _get_plugin_id_set(hm.get_plugins_available()) == {"simple_plugin", "simple_plugin_2"}
    assert _get_names_inside_folder(datadir / "plugins") == {
        "simple_plugin-1.0.0",
        "simple_plugin_2-1.0.0",
    }
    hm.remove_plugin("simple_plugin_2", Version("1.0.0"))
    assert _get_plugin_id_set(hm.get_plugins_available()) == {"simple_plugin"}
    assert _get_names_inside_folder(datadir / "plugins") == {"simple_plugin-1.0.0", ".trash"}
    assert _get_names_inside_folder(datadir / "plugins" / ".trash") == set()

    hm.remove_plugin("simple_plugin")
    assert _get_plugin_id_set(hm.get_plugins_available()) == set()
