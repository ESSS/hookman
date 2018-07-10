from pathlib import Path

import pytest


@pytest.fixture
def libs_path():
    return Path(__file__).parents[1] / 'build/libs'


@pytest.fixture
def plugins_path():
    return Path(__file__).parents[1] / 'tests/plugins'


@pytest.fixture
def simple_plugin_dir(datadir, plugins_path, libs_path):
    import os
    from shutil import copytree

    # Use the simple plugin available at plugins folder for this test
    plugin_dir = datadir / 'simple_plugin/'
    copytree(src=plugins_path / 'simple_plugin', dst=plugin_dir)

    # Get the compiled lib
    if os.sys.platform == 'win32':
        simple_plugin_dll = libs_path / 'simple_plugin.dll'
    else:
        simple_plugin_dll = libs_path / 'libsimple_plugin.so'

    from shutil import copy2
    copy2(src=simple_plugin_dll, dst=plugin_dir)

    return plugin_dir


@pytest.fixture
def simple_plugin_specs(plugins_path):
    # Load the hook_specs.py (inside the test folder) into plugin_specs
    hook_specs = plugins_path / 'simple_plugin/hook_specs.py'
    import importlib
    spec = importlib.util.spec_from_file_location('hook_specs', hook_specs)
    plugin_specs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin_specs)

    return plugin_specs.specs


@pytest.fixture
def load_hook_specs_from_path():
    # Load the hook_specs.py (inside the test folder) into plugin_specs

    def _load_hook_specs_from_path(path: Path):
        hook_specs = path
        import importlib
        spec = importlib.util.spec_from_file_location('hook_specs', hook_specs)
        plugin_specs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_specs)

        return plugin_specs.specs

    return _load_hook_specs_from_path
