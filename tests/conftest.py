from pathlib import Path

import pytest


@pytest.fixture
def plugins_zip_folder():
    return Path(__file__).parents[1] / 'build/plugin_zip'


@pytest.fixture
def plugins_folder():
    return Path(__file__).parents[1] / 'build/build_directory_for_tests/acme/plugin'


@pytest.fixture
def acme_hook_specs_file():
    return Path(__file__).parents[1] / 'tests/plugins/acme/hook_specs.py'


@pytest.fixture
def acme_hook_specs(acme_hook_specs_file):

    # Load the hook_specs.py (inside the test folder) into plugin_specs
    import importlib
    spec = importlib.util.spec_from_file_location('hook_specs', acme_hook_specs_file)
    plugin_specs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin_specs)

    return plugin_specs.specs


@pytest.fixture
def simple_plugin(datadir, plugins_folder, plugins_zip_folder, acme_hook_specs):
    plugin_dir = datadir / 'plugins/simple_plugin/'

    from shutil import copytree
    copytree(src=plugins_folder / 'simple_plugin', dst=plugin_dir)

    import sys
    if sys.platform == 'win32':
        plugin_zip_name = plugins_zip_folder / "simple_plugin-win64.hmplugin"
    else:
        plugin_zip_name = plugins_zip_folder / "simple_plugin-linux64.hmplugin"

    return {'path': plugin_dir, 'specs': acme_hook_specs, 'zip': plugin_zip_name}


@pytest.fixture
def simple_plugin_2(datadir, plugins_folder, plugins_zip_folder, acme_hook_specs):
    plugin_dir = datadir / 'plugins/simple_plugin_2/'

    from shutil import copytree
    copytree(src=plugins_folder / 'simple_plugin_2', dst=plugin_dir)

    import sys
    if sys.platform == 'win32':
        plugin_zip_name = plugins_zip_folder / "simple_plugin_2-win64.hmplugin"
    else:
        plugin_zip_name = plugins_zip_folder / "simple_plugin_2-linux64.hmplugin"

    return {'path': plugin_dir, 'specs': acme_hook_specs, 'zip': plugin_zip_name}
