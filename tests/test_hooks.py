import pytest

from hookman.hooks import HookMan, HooksSpecs


def test_hook_specs_without_arguments():

    def method_without_arguments() -> 'float':
        """
        test_method_without_arguments
        """

    # A hook must have parameters
    with pytest.raises(TypeError, match="It's not possible to create a hook without argument"):
        specs = HooksSpecs(project_name='acme', version='1', pyd_name='_acme',
            hooks=[method_without_arguments])


def test_hook_specs_with_missing_type_on_argument():

    def method_with_missing_type_on_argument(a: 'int', b) -> 'float':
        """
        fail_method_with_missing_type_on_argument
        """

    # A arguments of the hook must inform the type
    with pytest.raises(TypeError, match="All hooks arguments must have the type informed"):
        specs = HooksSpecs(project_name='acme', version='1', pyd_name='_acme',
            hooks=[method_with_missing_type_on_argument])


def test_hook_specs_without_docs_arguments():

    def method_with_docs_missing(a: 'int') -> 'int':
        pass  # pragma: no cover

    with pytest.raises(TypeError, match="All hooks must have documentation"):
        specs = HooksSpecs(project_name='acme', version='1', pyd_name='_acme',
            hooks=[method_with_docs_missing])


def test_get_hook_caller(simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])
    hook_caller = hm.get_hook_caller()
    friction_factor = hook_caller.friction_factor()
    env_temperature = hook_caller.env_temperature()
    assert friction_factor is not None
    assert env_temperature is None
    assert friction_factor(1, 2) == 3


def test_get_hook_caller_without_plugin(datadir, compiled_libs_folder, simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[datadir / 'some_non_existing_folder'])
    hook_caller = hm.get_hook_caller()
    friction_factor = hook_caller.friction_factor()
    env_temperature = hook_caller.env_temperature()
    assert friction_factor is None
    assert env_temperature is None


def test_plugins_available(datadir, simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[datadir / 'multiple_plugins'])
    plugins = hm.plugins_available()
    assert len(plugins) == 2
    assert list(plugins[0].keys()) == [
        'plugin_name',
        'plugin_version',
        'author',
        'email',
        'shared_lib',
        'description'
    ]


def test_install_plugin_without_lib(mocker, simple_plugin, plugins_zip_folder):
    from hookman import hookman_utils
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])

    mocked_config_content = {'shared_lib': 'NON_VALID_SHARED_LIB'}
    mocker.patch.object(hookman_utils, 'load_plugin_config_file', return_value=mocked_config_content)

    # Trying to install without a SHARED LIB inside the plugin
    from hookman.exceptions import PluginNotFound
    with pytest.raises(PluginNotFound, match=f"{mocked_config_content['shared_lib']} could not be found inside the plugin file"):
        hm.install_plugin(plugin_file_path=simple_plugin['zip'], dst_path=simple_plugin['path'])


def test_install_with_invalid_dst_path(simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])

    # Trying to install in the plugin on an different path informed on the construction of the HookMan object
    from hookman.exceptions import InvalidDestinationPath
    with pytest.raises(InvalidDestinationPath, match=f"Invalid destination path"):
        hm.install_plugin(plugin_file_path=simple_plugin['zip'], dst_path=simple_plugin['path'] / 'INVALID_PATH')


def test_install_plugin_with_invalid_file(mocker, simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])

    # Trying to install with a invalid file
    from hookman.exceptions import InvalidZipFile
    with pytest.raises(InvalidZipFile, match=f"is not a valid zip file"):
        hm.install_plugin(plugin_file_path=simple_plugin['zip'] / 'nonexistent_file', dst_path=simple_plugin['path'])


def test_install_plugin_duplicate(simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])
    import os
    os.makedirs(simple_plugin['path'] / 'simple_plugin')

    # Trying to install the plugin in a folder that already has a folder with the same name as the plugin
    from hookman.exceptions import PluginAlreadyInstalled
    with pytest.raises(PluginAlreadyInstalled, match=f"Plugin already installed"):
        hm.install_plugin(plugin_file_path=simple_plugin['zip'], dst_path=simple_plugin['path'])


def test_install_plugin(datadir, simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])
    assert (simple_plugin['path'] / 'simple_plugin').exists() == False
    hm.install_plugin(plugin_file_path=simple_plugin['zip'], dst_path=simple_plugin['path'])
    assert (simple_plugin['path'] / 'simple_plugin').exists() == True


def test_remove_plugin(datadir, simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[datadir / 'multiple_plugins'])

    assert len(hm.plugins_available()) == 2

    hm.remove_plugin('plugin_2')

    assert len(hm.plugins_available()) == 1
