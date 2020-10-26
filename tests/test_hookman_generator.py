from pathlib import Path

import pytest

from hookman.hookman_generator import HookManGenerator


def test_hook_man_generator(datadir, file_regression):
    # Pass a folder
    with pytest.raises(FileNotFoundError, match=f"File not found: *"):
        HookManGenerator(hook_spec_file_path=datadir)

    # Pass a invalid hook_spec_file (without specs)
    Path(datadir / "invalid_spec.py").touch()
    with pytest.raises(RuntimeError, match="Invalid file, specs not defined."):
        HookManGenerator(hook_spec_file_path=Path(datadir / "invalid_spec.py"))

    hg = HookManGenerator(hook_spec_file_path=Path(datadir / "hook_specs.py"))
    hg.generate_project_files(dst_path=datadir)

    file_regression.check(
        (datadir / "cpp" / "HookCaller.hpp").read_text(), basename="HookCaller", extension=".hpp"
    )
    file_regression.check(
        (datadir / "binding" / "HookCallerPython.cpp").read_text(),
        basename="HookCallerPython",
        extension=".cpp",
    )


def test_hook_man_generator_no_pyd(datadir, file_regression):
    hg = HookManGenerator(hook_spec_file_path=Path(datadir / "hook_specs_no_pyd.py"))
    hg.generate_project_files(dst_path=datadir)

    obtained_hook_caller_file = datadir / "cpp" / "HookCaller.hpp"
    file_regression.check(
        obtained_hook_caller_file.read_text(), basename="HookCallerNoPyd", extension=".hpp"
    )
    assert not (datadir / "binding").is_dir()


def test_generate_plugin_template(datadir, file_regression):
    plugin_dir = datadir / "test_generate_plugin_template"
    hg = HookManGenerator(hook_spec_file_path=Path(datadir / "hook_specs.py"))

    hg.generate_plugin_template(
        caption="Acme",
        plugin_id="acme",
        author_name="FOO",
        author_email="FOO@FOO.com",
        dst_path=plugin_dir,
    )

    obtained_hook_specs_file = datadir / "test_generate_plugin_template/acme/src/hook_specs.h"
    file_regression.check(
        obtained_hook_specs_file.read_text(), basename="generate_hook_specs", extension=".h"
    )

    obtained_plugin_yaml = datadir / "test_generate_plugin_template/acme/assets/plugin.yaml"
    file_regression.check(
        obtained_plugin_yaml.read_text(), basename="generate_plugin", extension=".yaml"
    )

    obtained_plugin_file = datadir / "test_generate_plugin_template/acme/src/acme.cpp"
    file_regression.check(
        obtained_plugin_file.read_text(), basename="generate_plugin", extension=".cpp"
    )

    obtained_readme = datadir / "test_generate_plugin_template/acme/assets/README.md"
    file_regression.check(obtained_readme.read_text(), basename="generate_README", extension=".md")

    obtained_cmake_list = datadir / "test_generate_plugin_template/acme/CMakeLists.txt"
    file_regression.check(
        obtained_cmake_list.read_text(), basename="generate_CMakeLists", extension=".txt"
    )

    obtained_cmake_list_src = datadir / "test_generate_plugin_template/acme/src/CMakeLists.txt"
    file_regression.check(
        obtained_cmake_list_src.read_text(), basename="generate_src_CMakeLists", extension=".txt"
    )

    obtained_compile_script = datadir / "test_generate_plugin_template/acme/compile.py"
    file_regression.check(
        obtained_compile_script.read_text(), basename="generate_compile", extension=".py"
    )


def test_generate_plugin_template_source_content_with_extra_includes(datadir, file_regression):
    plugin_dir = datadir / "test_generate_plugin_template_with_extra_include"
    hg = HookManGenerator(hook_spec_file_path=Path(datadir / "hook_specs.py"))

    hg.generate_plugin_template(
        caption="Acme",
        plugin_id="acme",
        author_name="FOO",
        author_email="FOO@FOO.com",
        dst_path=plugin_dir,
        extra_includes=["<my_sdk/sdk.h>"],
    )

    obtained_plugin_file = (
        datadir / "test_generate_plugin_template_with_extra_include/acme/src/acme.cpp"
    )
    file_regression.check(
        obtained_plugin_file.read_text(),
        basename="plugin_file_with_extra_includes",
        extension=".cpp",
    )


def test_generate_plugin_template_source_content_with_default_impls(datadir, file_regression):
    plugin_dir = datadir / "test_generate_plugin_template_source_content_with_default_impls"
    hg = HookManGenerator(hook_spec_file_path=Path(datadir / "hook_specs.py"))

    extra_body_lines = ["HOOK_FRICTION_FACTOR(v1, v2)", "{", "    return 0;", "}"]

    hg.generate_plugin_template(
        caption="Acme",
        plugin_id="acme",
        author_name="FOO",
        author_email="FOO@FOO.com",
        dst_path=plugin_dir,
        extra_body_lines=extra_body_lines,
        exclude_hooks=["HOOK_FRICTION_FACTOR"],
    )

    obtained_plugin_file = (
        datadir
        / "test_generate_plugin_template_source_content_with_default_impls/acme/src/acme.cpp"
    )
    file_regression.check(
        obtained_plugin_file.read_text(), basename="plugin_file_with_default_impl", extension=".cpp"
    )


def test_generate_plugin_template_source_wrong_arguments(datadir):
    hg = HookManGenerator(hook_spec_file_path=Path(datadir / "hook_specs.py"))

    with pytest.raises(ValueError, match="extra_includes parameter must be a list, got int"):
        hg._validate_parameter("extra_includes", 1)

    with pytest.raises(ValueError, match="All elements of extra_includes must be a string"):
        hg._validate_parameter("extra_includes", ["xx", 1])


def test_generate_hook_specs_header(datadir, file_regression):
    plugin_dir = datadir / "my-plugin"

    hg = HookManGenerator(hook_spec_file_path=Path(datadir / "hook_specs.py"))
    hg.generate_hook_specs_header(plugin_id="acme", dst_path=plugin_dir)

    obtained_hook_specs_file = plugin_dir / "acme/src/hook_specs.h"
    file_regression.check(
        obtained_hook_specs_file.read_text(), basename="generate_hook_specs_header1", extension=".h"
    )

    hg = HookManGenerator(hook_spec_file_path=Path(datadir / "hook_specs_2.py"))
    hg.generate_hook_specs_header(plugin_id="acme", dst_path=plugin_dir)
    file_regression.check(
        obtained_hook_specs_file.read_text(), basename="generate_hook_specs_header2", extension=".h"
    )


def test_generate_plugin_package_invalid_shared_lib_name(acme_hook_specs_file, tmpdir):
    hg = HookManGenerator(hook_spec_file_path=acme_hook_specs_file)

    from hookman.exceptions import HookmanError

    with pytest.raises(HookmanError):
        hg.generate_plugin_template(
            caption="acme",
            plugin_id="acm#e",
            author_email="acme1",
            author_name="acme2",
            dst_path=Path(tmpdir),
        )

    with pytest.raises(HookmanError):
        hg.generate_plugin_template(
            caption="acme",
            plugin_id="acm e",
            author_email="acme1",
            author_name="acme2",
            dst_path=Path(tmpdir),
        )

    with pytest.raises(HookmanError):
        hg.generate_plugin_template(
            caption="1acme",
            plugin_id="acm e",
            author_email="acme1",
            author_name="acme2",
            dst_path=Path(tmpdir),
        )


def test_generate_plugin_package(acme_hook_specs_file, tmpdir, mock_plugin_id_from_dll):
    hg = HookManGenerator(hook_spec_file_path=acme_hook_specs_file)
    plugin_id = "acme"
    hg.generate_plugin_template(
        caption="acme",
        plugin_id="acme",
        author_email="acme1",
        author_name="acme2",
        dst_path=Path(tmpdir),
        extras={"key": "override", "key2": "value2"},
    )
    plugin_dir = Path(tmpdir) / "acme"

    artifacts_dir = plugin_dir / "artifacts"
    artifacts_dir.mkdir()
    import sys

    shared_lib_name = f"{plugin_id}.dll" if sys.platform == "win32" else f"lib{plugin_id}.so"
    shared_lib_path = artifacts_dir / shared_lib_name
    shared_lib_path.write_text("")

    hg.generate_plugin_package(
        package_name="acme",
        plugin_dir=plugin_dir,
        extras_defaults={"key": "default", "key3": "default"},
    )

    from hookman.plugin_config import PluginInfo

    version = PluginInfo(Path(tmpdir / "acme/assets/plugin.yaml"), None).version

    win_plugin_name = f"{plugin_id}-{version}-win64.hmplugin"
    linux_plugin_name = f"{plugin_id}-{version}-linux64.hmplugin"
    hm_plugin_name = win_plugin_name if sys.platform == "win32" else linux_plugin_name

    compressed_plugin = plugin_dir / hm_plugin_name
    assert compressed_plugin.exists()

    from zipfile import ZipFile

    plugin_file_zip = ZipFile(compressed_plugin)
    list_of_files = [file.filename for file in plugin_file_zip.filelist]

    assert "assets/plugin.yaml" in list_of_files
    assert "assets/README.md" in list_of_files
    assert f"artifacts/{shared_lib_name}" in list_of_files

    with plugin_file_zip.open("assets/plugin.yaml", "r") as f:
        contents = f.read().decode("utf-8")

    from textwrap import dedent

    assert contents == dedent(
        """\
    author: acme2
    caption: acme
    email: acme1
    id: acme
    version: 1.0.0
    extras:
      key: override
      key2: value2
      key3: default
    """
    )


def test_generate_plugin_package_with_missing_folders(acme_hook_specs_file, tmpdir, mocker):
    import sys
    from textwrap import dedent
    from hookman.exceptions import (
        AssetsDirNotFoundError,
        ArtifactsDirNotFoundError,
        SharedLibraryNotFoundError,
    )

    hg = HookManGenerator(hook_spec_file_path=acme_hook_specs_file)
    plugin_dir = Path(tmpdir) / "acme"
    plugin_dir.mkdir()

    # -- Without Assets Folder
    with pytest.raises(AssetsDirNotFoundError):
        hg.generate_plugin_package(package_name="acme", plugin_dir=plugin_dir)

    asset_dir = plugin_dir / "assets"
    asset_dir.mkdir()

    # -- Without Artifacts Folder
    with pytest.raises(
        ArtifactsDirNotFoundError, match=r"Artifacts directory not found: .*[\\/]acme[\\/]artifacts"
    ):
        hg.generate_plugin_package(package_name="acme", plugin_dir=plugin_dir)

    artifacts_dir = plugin_dir / "artifacts"
    artifacts_dir.mkdir()

    # -- Without a shared library binary
    shared_lib_extension = "*.dll" if sys.platform == "win32" else "*.so"
    string_to_match = fr"Unable to locate a shared library ({shared_lib_extension}) in"
    import re

    with pytest.raises(FileNotFoundError, match=re.escape(string_to_match)):
        hg.generate_plugin_package(package_name="acme", plugin_dir=plugin_dir)

    lib_name = "test.dll" if sys.platform == "win32" else "libtest.so"
    shared_library_file = artifacts_dir / lib_name
    shared_library_file.write_text("")

    # -- Without Config file
    with pytest.raises(FileNotFoundError, match=f"Unable to locate the file plugin.yaml in"):
        hg.generate_plugin_package(package_name="acme", plugin_dir=plugin_dir)

    config_file = asset_dir / "plugin.yaml"
    config_file.write_text(
        dedent(
            f"""\
            caption: 'ACME'
            version: '1.0.0'

            author: 'acme_author'
            email: 'acme_email'

            id: 'acme'
        """
        )
    )
    # -- Without Readme file
    with pytest.raises(FileNotFoundError, match=f"Unable to locate the file README.md in"):
        hg.generate_plugin_package(package_name="acme", plugin_dir=plugin_dir)

    readme_file = asset_dir / "README.md"
    readme_file.write_text("")

    # # -- With a invalid shared_library name on config_file
    acme_lib_name = "acme.dll" if sys.platform == "win32" else "libacme.so"
    hm_plugin_name = (
        "acme-1.0.0-win64.hmplugin" if sys.platform == "win32" else "acme-1.0.0-linux64.hmplugin"
    )

    with pytest.raises(
        SharedLibraryNotFoundError, match=f"{acme_lib_name} could not be found in *"
    ):
        hg.generate_plugin_package(package_name="acme", plugin_dir=plugin_dir)

    acme_shared_library_file = artifacts_dir / acme_lib_name
    acme_shared_library_file.write_text("")

    # The mock bellow is to avoid to have get a valid dll on this test
    from hookman.plugin_config import PluginInfo

    mocker.patch.object(PluginInfo, "_get_plugin_id_from_dll", return_value="")

    hg.generate_plugin_package(package_name="acme", plugin_dir=plugin_dir)
    compressed_plugin_package = plugin_dir / hm_plugin_name
    assert compressed_plugin_package.exists()


def test_generate_plugin_package_invalid_version(
    acme_hook_specs_file, tmp_path, mocker, mock_plugin_id_from_dll
):
    hg = HookManGenerator(hook_spec_file_path=acme_hook_specs_file)
    plugin_id = "acme"
    hg.generate_plugin_template(plugin_id, plugin_id, "acme1", "acme2", tmp_path)

    plugin_yaml = tmp_path / "acme/assets/plugin.yaml"
    new_content = plugin_yaml.read_text().replace("version: '1.0.0'", "version: '1'")
    plugin_yaml.write_text(new_content)

    mocker.patch(
        "hookman.hookman_generator.HookManGenerator._validate_package_folder", return_value=None
    )

    with pytest.raises(
        ValueError, match="Version attribute does not follow semantic version, got '1'"
    ):
        hg.generate_plugin_package(plugin_id, plugin_dir=tmp_path / plugin_id)
