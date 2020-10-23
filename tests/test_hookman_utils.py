import sys

import pytest


def test_find_config_files(datadir):
    from hookman.hookman_utils import find_config_files

    config_files = find_config_files(datadir)
    assert len(config_files) == 2

    config_files = find_config_files(datadir, ignored_sub_dir_names=["fizzbuzz"])
    assert len(config_files) == 2

    config_files = find_config_files(datadir, ignored_sub_dir_names=["foo"])
    assert len(config_files) == 1

    config_files = find_config_files(datadir, ignored_sub_dir_names=["foo", "bar"])
    assert len(config_files) == 0

    config_files = find_config_files([datadir / "non_existing_folder"])
    assert len(config_files) == 0


@pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="path only needs changing on Windows"
)
def test_change_path_env(simple_plugin_dll):
    import os
    from hookman.hookman_utils import change_path_env

    dll_dir = str(simple_plugin_dll.parent)
    assert not dll_dir in os.environ["PATH"]
    with change_path_env(str(simple_plugin_dll)):
        assert dll_dir in os.environ["PATH"]
    assert not dll_dir in os.environ["PATH"]


@pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="path only needs changing on Windows"
)
def test_path_change_when_load_library(simple_plugin_dll, mocker):
    mocker.patch("hookman.hookman_utils.change_path_env")
    from hookman.hookman_utils import change_path_env, load_shared_lib

    with load_shared_lib(str(simple_plugin_dll)):
        pass
    change_path_env.assert_called_once()
