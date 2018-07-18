from pathlib import Path

import pytest


@pytest.fixture
def compiled_libs_folder():
    return Path(__file__).parents[1] / 'build/libs'


@pytest.fixture
def plugins_zip_folder():
    return Path(__file__).parents[1] / 'build/plugin_zip'


@pytest.fixture
def plugins_folder():
    return Path(__file__).parents[1] / 'tests/plugins'


@pytest.fixture
def simple_plugin(datadir, plugins_folder, compiled_libs_folder, plugins_zip_folder):
    import os
    from shutil import copytree

    # Use the simple plugin available at plugins folder for this test
    plugin_dir = datadir / 'simple_plugin/'
    copytree(src=plugins_folder / 'simple_plugin', dst=plugin_dir)

    # Get the compiled lib
    if os.sys.platform == 'win32':
        simple_plugin_dll = compiled_libs_folder / 'simple_plugin.dll'
    else:
        simple_plugin_dll = compiled_libs_folder / 'libsimple_plugin.so'

    from shutil import copy2
    copy2(src=simple_plugin_dll, dst=plugin_dir)

    # Load the hook_specs.py (inside the test folder) into plugin_specs
    hook_specs = plugins_folder / 'simple_plugin/hook_specs.py'
    import importlib
    spec = importlib.util.spec_from_file_location('hook_specs', hook_specs)
    plugin_specs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin_specs)

    simple_plugin_zip_file = plugins_zip_folder / 'simple_plugin.zip'

    simple_plugin = {'path': plugin_dir, 'specs': plugin_specs.specs, 'zip': simple_plugin_zip_file}
    return simple_plugin

# @pytest.fixture
# def simple_plugin_specs(plugins_folder):
#     # Load the hook_specs.py (inside the test folder) into plugin_specs
#     hook_specs = plugins_folder / 'simple_plugin/hook_specs.py'
#     import importlib
#     spec = importlib.util.spec_from_file_location('hook_specs', hook_specs)
#     plugin_specs = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(plugin_specs)
#
#     return plugin_specs.specs
