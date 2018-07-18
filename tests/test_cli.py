from click.testing import CliRunner

from hookman import cli


def test_command_line_interface(datadir):
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 2
    assert result.output == 'Usage: main [OPTIONS] SPECS_PATH\n\nError: Missing argument "specs_path".\n'

    hook_spec_file = str(datadir / 'hook_specs.py')
    result = runner.invoke(cli.main, [hook_spec_file, '--dst-path', datadir])
    assert result.exit_code == 0

    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
