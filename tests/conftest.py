from pathlib import Path

import pytest



@pytest.fixture
def libs_path():
    return Path(__file__).parents[1] / 'build/libs'


# @pytest.fixture
# def plugin_path(datadir, libs_path) -> Path:
#     from shutil import copy2
#     simple_plugin_dll = libs_path / 'simple_plugin.dll'
#     dst_path = datadir / 'plugin'
#     copy2(src=simple_plugin_dll, dst=dst_path)
#     return dst_path
