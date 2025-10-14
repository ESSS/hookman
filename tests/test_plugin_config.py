# mypy: allow-untyped-defs
import re
from pathlib import Path
from textwrap import dedent

import pytest
from pytest_mock import MockerFixture
from strictyaml import YAMLValidationError

from hookman.plugin_config import PluginInfo


def test_load_config_content(datadir, mocker, mock_plugin_id_from_dll) -> None:
    mocker.patch.object(PluginInfo, "_get_hooks_implemented", return_value=["a"])

    hooks_available = {
        "friction_factor": "acme_v1_friction_factor",
        "env_temperature": "acme_v1_env_temperature",
    }
    plugin_yaml_file = datadir / "assets/plugin.yaml"

    config_file_content = PluginInfo(plugin_yaml_file, hooks_available)
    assert config_file_content is not None

    with pytest.raises(FileNotFoundError):
        PluginInfo(datadir / "NonValid", hooks_available)


def test_get_shared_libs_path(datadir, mocker, mock_plugin_id_from_dll) -> None:
    mocker.patch("sys.platform", "linux")

    expected_path = datadir / "artifacts/libname_of_the_shared_lib.so"
    plugin_config = PluginInfo(datadir / "assets/plugin.yaml", hooks_available=None)
    assert plugin_config.shared_lib_path == expected_path

    mocker.patch("sys.platform", "win32")

    expected_path = datadir / "artifacts/name_of_the_shared_lib.dll"
    plugin_config = PluginInfo(datadir / "assets/plugin.yaml", hooks_available=None)
    assert plugin_config.shared_lib_path == expected_path


def test_plugin_id_conflict(simple_plugin, datadir) -> None:
    yaml_file = simple_plugin["path"] / "assets/plugin.yaml"
    assert PluginInfo(yaml_file, None)

    import sys

    shared_lib_name = f"simple_plugin.dll" if sys.platform == "win32" else f"libsimple_plugin.so"
    shared_lib_executable = simple_plugin["path"] / f"artifacts/{shared_lib_name}"

    acme_lib_name = shared_lib_name.replace("simple_plugin", "ACME")
    acme_lib = simple_plugin["path"] / f"artifacts/{acme_lib_name}"
    shared_lib_executable.rename(acme_lib)

    new_content = yaml_file.read_text().replace("simple_plugin", "ACME")
    yaml_file.write_text(new_content)

    expected_msg = (
        'Error, the plugin_id inside plugin.yaml is "ACME" '
        f"while the plugin_id inside the {acme_lib_name} is simple_plugin"
    )
    with pytest.raises(RuntimeError, match=expected_msg):
        PluginInfo(yaml_file, None)


def testPluginInfoInvalidSchema(tmp_path: Path, mocker: MockerFixture) -> None:
    invalid_yaml_content = f"""\
            caption: 'Plugin'
            version: '1.0.0'
            author: 'ESSS'
            developer: 'Developer 1'
            email: 'alfasim-dev@esss.co'
            id: 'plugin'
            """

    invalid_yaml_file = tmp_path / "config.yaml"
    invalid_yaml_file.write_text(invalid_yaml_content)

    mocker.patch.object(PluginInfo, "_check_if_shared_lib_exists", autospec=True)
    mocker.patch.object(PluginInfo, "_get_plugin_id_from_dll", autospc=True, return_value="plugin")

    current_schema = dedent(
        """\
    caption : Str()
    version : Str()
    author : Str()
    email : Str()
    id : Str()
    Optional("requirements") : MapPattern(Str(), Str())
    Optional("extras") : MapPattern(Str(), Str())
    """
    ).strip()
    expected_message = f"The plugin.yaml does not follow the PLUGIN_CONFIG_SCHEMA: {current_schema}"
    with pytest.raises(ValueError, match=re.escape(expected_message)):
        info = PluginInfo(invalid_yaml_file)
