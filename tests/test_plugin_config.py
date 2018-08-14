import pytest

from hookman.plugin_config import PluginInfo


def test_load_config_content(datadir, mocker):
    mocker.patch.object(PluginInfo, '_get_hooks_implemented', return_value=['a'])
    hooks_available = {'friction_factor': 'acme_v1_friction_factor', 'env_temperature': 'acme_v1_env_temperature'}
    plugin_yaml_file = datadir / 'assets/plugin.yaml'

    config_file_content = PluginInfo(plugin_yaml_file, hooks_available)
    assert config_file_content is not None

    with pytest.raises(FileNotFoundError):
        PluginInfo(datadir / 'NonValid', hooks_available)


def test_get_shared_libs_path(datadir, mocker):
    mocker.patch('sys.platform', 'linux')

    expected_path = datadir / 'artifacts/libname_of_the_shared_lib.so'
    plugin_config = PluginInfo(datadir / 'assets/plugin.yaml', hooks_available=None)
    assert plugin_config.shared_lib_path == expected_path

    mocker.patch('sys.platform', 'win32')

    expected_path = datadir / 'artifacts/name_of_the_shared_lib.dll'
    plugin_config = PluginInfo(datadir / 'assets/plugin.yaml', hooks_available=None)
    assert plugin_config.shared_lib_path == expected_path
