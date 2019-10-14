from pathlib import Path

import pytest


@pytest.fixture
def plugins_zip_folder():
    return Path(__file__).parents[1] / "build/plugin_zip"


@pytest.fixture
def plugins_folder():
    return Path(__file__).parents[1] / "build/build_directory_for_tests/acme/plugin"


@pytest.fixture
def acme_hook_specs_file():
    return Path(__file__).parents[1] / "tests/plugins/acme/hook_specs.py"


@pytest.fixture
def acme_hook_specs(acme_hook_specs_file):

    # Load the hook_specs.py (inside the test folder) into plugin_specs
    import importlib

    spec = importlib.util.spec_from_file_location("hook_specs", acme_hook_specs_file)
    plugin_specs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin_specs)

    return plugin_specs.specs


@pytest.fixture
def simple_plugin_dll(datadir, plugins_folder):
    plugin_dir = datadir / "simple_plugin/"

    from shutil import copytree

    copytree(src=plugins_folder / "simple_plugin/artifacts", dst=plugin_dir)

    return plugin_dir / "simple_plugin.dll"


@pytest.fixture
def get_plugin(datadir, plugins_folder, plugins_zip_folder, acme_hook_specs):
    def _get_plugin(plugin_name):
        plugin_dir = datadir / f"plugins/{plugin_name}/"

        from shutil import copytree

        copytree(src=plugins_folder / plugin_name, dst=plugin_dir)
        from hookman.plugin_config import PluginInfo

        version = PluginInfo(plugin_dir / "assets/plugin.yaml", hooks_available=None).version
        name = f"{plugin_name}-{version}"
        import sys

        hm_plugin_name = (
            f"{name}-win64.hmplugin" if sys.platform == "win32" else f"{name}-linux64.hmplugin"
        )
        plugin_zip_path = plugins_zip_folder / hm_plugin_name

        return {"path": plugin_dir, "specs": acme_hook_specs, "zip": plugin_zip_path}

    return _get_plugin


@pytest.fixture
def simple_plugin(get_plugin):
    return get_plugin("simple_plugin")


@pytest.fixture
def simple_plugin_2(get_plugin):
    return get_plugin("simple_plugin_2")


@pytest.fixture
def mock_plugin_id_from_dll(mocker):
    # The mock bellow is to avoid to have get a valid dll on this test
    from hookman.plugin_config import PluginInfo

    mocker.patch.object(PluginInfo, "_get_plugin_id_from_dll", return_value="")
