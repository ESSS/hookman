import pytest

from hookman.hooks import HookMan, HookSpecs, PluginInfo


def test_hook_specs_without_arguments():

    def method_without_arguments() -> 'float':
        """
        test_method_without_arguments
        """

    # A hook must have parameters
    with pytest.raises(TypeError, match="It's not possible to create a hook without argument"):
        specs = HookSpecs(project_name='acme', version='1', pyd_name='_acme', hooks=[method_without_arguments])


def test_hook_specs_with_missing_type_on_argument():

    def method_with_missing_type_on_argument(a: 'int', b) -> 'float':
        """
        fail_method_with_missing_type_on_argument
        """

    # A arguments of the hook must inform the type
    with pytest.raises(TypeError, match="All hooks arguments must have the type informed"):
        specs = HookSpecs(project_name='acme', version='1', pyd_name='_acme', hooks=[method_with_missing_type_on_argument])


def test_hook_specs_without_docs_arguments():

    def method_with_docs_missing(a: 'int') -> 'int':
        pass  # pragma: no cover

    with pytest.raises(TypeError, match="All hooks must have documentation"):
        specs = HookSpecs(project_name='acme', version='1', pyd_name='_acme', hooks=[method_with_docs_missing])


def test_get_hook_caller_with_conflict(simple_plugin, simple_plugin_2):
    plugins_dirs = [simple_plugin['path'], simple_plugin_2['path']]
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=plugins_dirs)
    hc = hm.get_hook_caller()
    assert len(hc.friction_factor_impls()) == 2
    assert len(hc.env_temperature_impls()) == 1


def test_get_hook_caller(simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])
    hook_caller = hm.get_hook_caller()
    friction_factors = hook_caller.friction_factor_impls()
    env_temperatures = hook_caller.env_temperature_impls()
    assert len(friction_factors) == 1
    assert len(env_temperatures) == 0
    assert friction_factors[0](1, 2) == 3


def test_get_hook_caller_passing_ignored_plugins(datadir, simple_plugin, simple_plugin_2):
    plugins_dirs = [simple_plugin['path'], simple_plugin_2['path']]
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=plugins_dirs)

    assert len(hm.get_plugins_available()) == 2
    assert len(list((datadir / 'plugins').iterdir())) == 2

    hook_caller = hm.get_hook_caller(ignored_plugins=['Simple Plugin 2'])
    env_temperatures = hook_caller.env_temperature_impls()

    # Plugin2 implements the Hook env_temperature
    assert len(env_temperatures) == 0


def test_get_hook_caller_without_plugin(datadir, simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[datadir / 'some_non_existing_folder'])
    hook_caller = hm.get_hook_caller()
    friction_factors = hook_caller.friction_factor_impls()
    env_temperatures = hook_caller.env_temperature_impls()
    assert len(friction_factors) == 0
    assert len(env_temperatures) == 0


def test_plugins_available(simple_plugin, simple_plugin_2):
    plugin_dirs = [simple_plugin['path'], simple_plugin_2['path']]
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=plugin_dirs)
    plugins = hm.get_plugins_available()
    assert len(plugins) == 2
    import attr
    assert list(attr.asdict(plugins[0]).keys()) == [
        'yaml_location',
        'hooks_available',

        'author',
        'description',
        'email',
        'hooks_implemented',
        'name',
        'shared_lib_name',
        'shared_lib_path',
        'version',
    ]

    plugins = hm.get_plugins_available(ignored_plugins=['Simple Plugin 2'])
    assert len(plugins) == 1


def test_install_plugin_without_lib(mocker, simple_plugin, plugins_zip_folder):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])

    mocked_config_content = {'shared_lib_name': 'NON_VALID_SHARED_LIB'}
    mocker.patch.object(PluginInfo, '_load_yaml_file', return_value=mocked_config_content)

    # Trying to install without a SHARED LIB inside the plugin
    from hookman.exceptions import SharedLibraryNotFoundError
    with pytest.raises(SharedLibraryNotFoundError, match=f"{mocked_config_content['shared_lib_name']} could not be found inside the plugin file"):
        hm.install_plugin(plugin_file_path=simple_plugin['zip'], dst_path=simple_plugin['path'])


def test_install_with_invalid_dst_path(simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])

    # Trying to install in the plugin on an different path informed on the construction of the HookMan object
    from hookman.exceptions import InvalidDestinationPathError
    with pytest.raises(InvalidDestinationPathError, match=f"Invalid destination path"):
        hm.install_plugin(plugin_file_path=simple_plugin['zip'], dst_path=simple_plugin['path'] / 'INVALID_PATH')


def test_install_plugin_duplicate(simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path'].parent])
    import os
    os.makedirs(simple_plugin['path'] / 'simple_plugin')

    # Trying to install the plugin in a folder that already has a folder with the same name as the plugin
    from hookman.exceptions import PluginAlreadyInstalledError
    with pytest.raises(PluginAlreadyInstalledError, match=f"Plugin already installed"):
        hm.install_plugin(plugin_file_path=simple_plugin['zip'], dst_path=simple_plugin['path'].parent)


def test_install_plugin(datadir, simple_plugin):
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=[simple_plugin['path']])
    assert (simple_plugin['path'] / 'simple_plugin').exists() == False
    hm.install_plugin(plugin_file_path=simple_plugin['zip'], dst_path=simple_plugin['path'])
    assert (simple_plugin['path'] / 'simple_plugin').exists() == True


def test_remove_plugin(datadir, simple_plugin, simple_plugin_2):
    plugins_dirs = [simple_plugin['path'], simple_plugin_2['path']]
    hm = HookMan(specs=simple_plugin['specs'], plugin_dirs=plugins_dirs)

    assert len(hm.get_plugins_available()) == 2
    assert len(list((datadir / 'plugins').iterdir())) == 2
    hm.remove_plugin('Simple Plugin 2')
    assert len(hm.get_plugins_available()) == 1
    assert len(list((datadir / 'plugins').iterdir())) == 1
