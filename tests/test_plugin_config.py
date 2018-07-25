import pytest

from hookman.plugin_config import PluginInfo


def test_load_config_content(datadir):
    plugin_yaml_file = datadir / 'plugin.yaml'
    config_file_content = PluginInfo(plugin_yaml_file)
    assert config_file_content is not None
    with pytest.raises(FileNotFoundError):
        PluginInfo(datadir / 'NonValid')


def test_get_shared_libs_path(datadir, mocker):
    mocker.patch('sys.platform', 'linux')
    expected_path = datadir / 'libname_of_the_shared_lib.so'
    plugin_config = PluginInfo(datadir / 'plugin.yaml')
    assert plugin_config.shared_lib_path == expected_path

    mocker.patch('sys.platform', 'win32')
    expected_path = datadir / 'name_of_the_shared_lib.dll'
    plugin_config = PluginInfo(datadir / 'plugin.yaml')
    assert plugin_config.shared_lib_path == expected_path

