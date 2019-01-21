from click.testing import CliRunner

from hookman import __main__


def test_command_line_interface(datadir):
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(__main__.main)
    assert result.exit_code == 2
    assert result.output == 'Usage: main [OPTIONS] SPECS_PATH\nTry "main --help" for help.' \
                            '\n\nError: Missing argument "SPECS_PATH".\n'

    hook_spec_file = str(datadir / 'hook_specs.py')
    result = runner.invoke(__main__.main, [hook_spec_file, '--dst-path', datadir])
    assert result.exit_code == 0

    help_result = runner.invoke(__main__.main, ['--help'])
    assert help_result.exit_code == 0
