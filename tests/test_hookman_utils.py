import pytest


def test_find_config_files(datadir):
    from hookman.hookman_utils import find_config_files
    config_files = find_config_files(datadir)
    assert len(config_files) == 1

    config_files = find_config_files([datadir / 'non_existing_folder'])
    assert len(config_files) == 0
