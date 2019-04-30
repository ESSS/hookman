import sys

import pytest


def test_find_config_files(datadir):
    from hookman.hookman_utils import find_config_files
    config_files = find_config_files(datadir)
    assert len(config_files) == 1

    config_files = find_config_files([datadir / 'non_existing_folder'])
    assert len(config_files) == 0


@pytest.mark.skipif(not sys.platform.startswith("win"), reason='path only needs changing on Windows')
def test_path_change_when_loading_shared_lib(simple_plugin_dll):
    import os
    from pathlib import Path
    from hookman.hookman_utils import load_shared_lib
    assert not str(simple_plugin_dll.parent) in os.environ["PATH"]
    with load_shared_lib(str(simple_plugin_dll)):
        pass
    paths = os.environ["PATH"].split(os.pathsep)
    assert Path(paths[0]) == simple_plugin_dll.parent
