import pytest


def test_find_config_files(datadir):
    from hookman.hookman_utils import find_config_files
    config_files = find_config_files(datadir)
    assert len(config_files) == 1

    config_files = find_config_files([datadir / 'non_existing_folder'])
    assert len(config_files) == 0


def test_load_shared_lib(simple_plugin_dll):
    import os
    import sys
    from hookman.hookman_utils import load_shared_lib

    if sys.platform.startswith('win'):
        assert not str(simple_plugin_dll.parent) in os.environ["PATH"]
        with load_shared_lib(str(simple_plugin_dll)):
            pass

        assert str(simple_plugin_dll.parent) in os.environ["PATH"]
