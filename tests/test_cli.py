import sys

from _pytest.pytester import LineMatcher
from click.testing import CliRunner

from hookman import __main__


def test_help(datadir):
    runner = CliRunner()
    result = runner.invoke(__main__.cli)
    assert result.exit_code == 0, result.output
    matcher = LineMatcher(result.output.splitlines())
    matcher.fnmatch_lines(
        [
            "Commands:",
            "  generate-plugin-template *",
            "  generate-project-files *",
            "  package-plugin *",
        ]
    )


def test_generate_project_files(datadir):
    runner = CliRunner()
    hook_spec_file = str(datadir / "hook_specs.py")
    result = runner.invoke(
        __main__.cli, ["generate-project-files", hook_spec_file, "--dst-path", datadir]
    )
    assert result.exit_code == 0, result.output

    assert (datadir / "cpp" / "HookCaller.hpp").is_file()
    assert (datadir / "binding" / "HookCallerPython.cpp").is_file()


def test_generate_plugin_template(datadir):
    runner = CliRunner()
    hook_spec_file = str(datadir / "hook_specs.py")
    result = runner.invoke(
        __main__.cli,
        [
            "generate-plugin-template",
            hook_spec_file,
            "My Plugin",
            "my_plugin",
            "Jonh",
            "jonh@somewhere",
            "--dst-path",
            datadir,
        ],
    )
    assert result.exit_code == 0, result.output

    assert (datadir / "my_plugin" / "assets" / "plugin.yaml").is_file()
    assert (datadir / "my_plugin" / "src" / "my_plugin.cpp").is_file()
    assert (datadir / "my_plugin" / "src" / "hook_specs.h").is_file()


def test_generate_hook_specs_h(datadir):
    runner = CliRunner()
    hook_spec_file = str(datadir / "hook_specs.py")
    result = runner.invoke(
        __main__.cli, ["generate-hook-specs-h", hook_spec_file, "my_plugin", "--dst-path", datadir]
    )
    assert result.exit_code == 0, result.output

    assert (datadir / "my_plugin" / "src" / "hook_specs.h").is_file()


def test_package_plugin(datadir, mock_plugin_id_from_dll):
    runner = CliRunner()
    hook_spec_file = str(datadir / "hook_specs.py")
    result = runner.invoke(
        __main__.cli,
        [
            "generate-plugin-template",
            hook_spec_file,
            "My Plugin",
            "my_plugin",
            "Jonh",
            "jonh@somewhere",
            "--dst-path",
            datadir,
        ],
    )
    assert result.exit_code == 0, result.output

    assert (datadir / "my_plugin" / "assets" / "plugin.yaml").is_file()
    assert (datadir / "my_plugin" / "src" / "my_plugin.cpp").is_file()

    # create dummy artifact
    prefix, ext = ("", ".dll") if sys.platform.startswith("win") else ("lib", ".so")
    lib = datadir / "my_plugin" / "artifacts" / f"{prefix}my_plugin{ext}"
    lib.parent.mkdir()
    lib.write_text("")

    result = runner.invoke(
        __main__.cli,
        [
            "package-plugin",
            hook_spec_file,
            "my-plugin-1.0",
            str(datadir / "my_plugin"),
            "--dst-path",
            datadir,
        ],
    )
    assert result.exit_code == 0, result.output
    assert str(datadir / "my-plugin-1.0.hmplugin")
