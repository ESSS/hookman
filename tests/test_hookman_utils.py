import pytest


def test_find_config_files(datadir):
    from hookman.hookman_utils import find_config_files
    config_files = find_config_files(datadir)
    assert len(config_files) == 1

    config_files = find_config_files([datadir / 'non_existing_folder'])
    assert len(config_files) == 0


def test_load_config_content(datadir):
    from hookman.hookman_utils import load_plugin_config_file
    plugin_yaml_file = datadir / 'plugin.yaml'
    config_file_content = load_plugin_config_file(plugin_yaml_file.read_text(encoding="utf-8"))
    assert config_file_content is not None

    with pytest.raises(TypeError, match="StrictYAML can only read a string of valid YAML"):
        load_plugin_config_file(datadir / 'NonValid')


def test_get_shared_libs_path(datadir, mocker):
    from hookman.hookman_utils import get_shared_libs_path

    mocker.patch('os.sys.platform', 'linux')
    expected_path = datadir / 'libname_of_the_shared_lib.so'
    assert get_shared_libs_path(datadir / 'plugin.yaml') == [expected_path]

    mocker.patch('os.sys.platform', 'win32')
    expected_path = datadir / 'name_of_the_shared_lib.dll'
    assert get_shared_libs_path(datadir / 'plugin.yaml') == [expected_path]
