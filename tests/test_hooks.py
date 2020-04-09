import pytest

from hookman.hooks import HookMan, HookSpecs, PluginInfo


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


def test_hook_specs_without_arguments():
    def method_without_arguments() -> "float":
        """
        test_method_without_arguments
        """

    # A hook must have parameters
    with pytest.raises(TypeError, match="It's not possible to create a hook without argument"):
        specs = HookSpecs(
            project_name="acme", version="1", pyd_name="_acme", hooks=[method_without_arguments]
        )


def test_hook_specs_with_missing_type_on_argument():
    def method_with_missing_type_on_argument(a: "int", b) -> "float":
        """
        fail_method_with_missing_type_on_argument
        """

    # A arguments of the hook must inform the type
    with pytest.raises(TypeError, match="All hooks arguments must have the type informed"):
        specs = HookSpecs(
            project_name="acme",
            version="1",
            pyd_name="_acme",
            hooks=[method_with_missing_type_on_argument],
        )


def test_hook_specs_without_docs_arguments():
    def method_with_docs_missing(a: "int") -> "int":
        pass  # pragma: no cover

    with pytest.raises(TypeError, match="All hooks must have documentation"):
        specs = HookSpecs(
            project_name="acme", version="1", pyd_name="_acme", hooks=[method_with_docs_missing]
        )


def test_get_hook_caller_with_conflict(simple_plugin, simple_plugin_2):
    plugins_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugins_dirs)
    hc = hm.get_hook_caller()
    assert len(hc.friction_factor_impls()) == 2
    assert len(hc.env_temperature_impls()) == 1


def test_get_hook_caller(simple_plugin):
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[simple_plugin["path"]])
    hook_caller = hm.get_hook_caller()
    friction_factors = hook_caller.friction_factor_impls()
    env_temperatures = hook_caller.env_temperature_impls()
    assert len(friction_factors) == 1
    assert len(env_temperatures) == 0
    assert friction_factors[0](1, 2) == 3

    # Call a hook for a specific plugin implementation
    assert hook_caller.friction_factor_impl("simple_plugin")(1, 2) == 3


def test_get_hook_caller_passing_ignored_plugins(datadir, simple_plugin, simple_plugin_2):
    plugins_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugins_dirs)

    assert len(hm.get_plugins_available()) == 2
    assert len(list((datadir / "plugins").iterdir())) == 2

    hook_caller = hm.get_hook_caller(ignored_plugins=["simple_plugin_2"])
    env_temperatures = hook_caller.env_temperature_impls()

    # Plugin2 implements the Hook env_temperature
    assert len(env_temperatures) == 0


def test_get_hook_caller_without_plugin(datadir, simple_plugin):
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[datadir / "some_non_existing_folder"])
    hook_caller = hm.get_hook_caller()
    friction_factors = hook_caller.friction_factor_impls()
    env_temperatures = hook_caller.env_temperature_impls()
    assert len(friction_factors) == 0
    assert len(env_temperatures) == 0


def test_plugins_available_plain(simple_plugin, simple_plugin_2):
    plugin_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugin_dirs)
    plugins = hm.get_plugins_available()
    assert len(plugins) == 2
    import attr

    assert list(attr.asdict(plugins[0]).keys()) == [
        "yaml_location",
        "hooks_available",
        "author",
        "description",
        "email",
        "hooks_implemented",
        "caption",
        "shared_lib_name",
        "shared_lib_path",
        "version",
        "extras",
    ]

    plugins = hm.get_plugins_available(ignored_plugins=["simple_plugin_2"])
    assert len(plugins) == 1


def test_plugins_available_ignore_trash(datadir, simple_plugin, simple_plugin_2):
    plugin_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugin_dirs)

    plugins = hm.get_plugins_available()
    assert {p.id for p in plugins} == {"simple_plugin", "simple_plugin_2"}

    hm._move_to_trash(datadir / "plugins", "simple_plugin")
    plugins = hm.get_plugins_available()
    assert {p.id for p in plugins} == {"simple_plugin_2"}

    hm._move_to_trash(datadir / "plugins", "simple_plugin_2")
    plugins = hm.get_plugins_available()
    assert {p.id for p in plugins} == set()


def test_try_clean_cache_ignore_os_errors(datadir, simple_plugin, monkeypatch):
    import sys

    # Windows has problems deleting filer/folders in used.
    win = sys.platform.startswith("win32")

    plugin_dir = datadir / "plugins"
    trash_folder = plugin_dir / ".trash"
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugin_dir)
    hm._move_to_trash(plugin_dir, "simple_plugin")
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


def test_install_plugin_without_lib(mocker, simple_plugin, plugins_zip_folder):
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


def test_install_with_invalid_dest_path(simple_plugin):
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[simple_plugin["path"]])

    # Trying to install in the plugin on an different path informed on the construction of the HookMan object
    from hookman.exceptions import InvalidDestinationPathError

    with pytest.raises(InvalidDestinationPathError, match=f"Invalid destination path"):
        hm.install_plugin(
            plugin_file_path=simple_plugin["zip"], dest_path=simple_plugin["path"] / "INVALID_PATH"
        )


def test_install_plugin_duplicate(simple_plugin):
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[simple_plugin["path"].parent])
    import os

    os.makedirs(simple_plugin["path"] / "simple_plugin")

    # Trying to install the plugin in a folder that already has a folder with the same name as the plugin
    from hookman.exceptions import PluginAlreadyInstalledError

    with pytest.raises(PluginAlreadyInstalledError, match=f"Plugin already installed"):
        hm.install_plugin(
            plugin_file_path=simple_plugin["zip"], dest_path=simple_plugin["path"].parent
        )


def test_install_plugin(datadir, simple_plugin):
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=[simple_plugin["path"]])
    assert (simple_plugin["path"] / "simple_plugin").exists() == False
    hm.install_plugin(plugin_file_path=simple_plugin["zip"], dest_path=simple_plugin["path"])
    assert (simple_plugin["path"] / "simple_plugin").exists() == True


def test_remove_plugin(datadir, simple_plugin, simple_plugin_2):
    plugins_dirs = [simple_plugin["path"], simple_plugin_2["path"]]
    hm = HookMan(specs=simple_plugin["specs"], plugin_dirs=plugins_dirs)

    assert _get_plugin_id_set(hm.get_plugins_available()) == {"simple_plugin", "simple_plugin_2"}
    assert _get_names_inside_folder(datadir / "plugins") == {"simple_plugin", "simple_plugin_2"}
    hm.remove_plugin("simple_plugin_2")
    assert _get_plugin_id_set(hm.get_plugins_available()) == {"simple_plugin"}
    assert _get_names_inside_folder(datadir / "plugins") == {"simple_plugin", ".trash"}
    assert _get_names_inside_folder(datadir / "plugins" / ".trash") == set()
