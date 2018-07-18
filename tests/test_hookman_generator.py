from pathlib import Path

import pytest

from hookman.hookman_generator import HookManGenerator


def test_hook_man_generator(datadir):

    # Pass a folder
    with pytest.raises(FileNotFoundError, match=f"File not found: *"):
        HookManGenerator(hook_spec_file_path=datadir)

    # Pass a invalid hook_spec_file (without specs)
    Path(datadir / 'invalid_spec.py').touch()
    with pytest.raises(RuntimeError, match="Invalid file, specs not defined."):
        HookManGenerator(hook_spec_file_path=Path(datadir / 'invalid_spec.py'))

    hg = HookManGenerator(hook_spec_file_path=Path(datadir / 'hook_specs.py'))
    hg.generate_files(dst_path=datadir)

    obtained_hook_specs_file = datadir / 'plugin' / 'hook_specs.h'
    expected_hook_specs_file = datadir / 'expected_hook_specs.h'

    obtained_hook_caller_file = datadir / 'cpp' / 'HookCaller.hpp'
    expected_hook_caller_file = datadir / 'ExpectedHookCaller.hpp'

    obtained_hook_caller_python_file = datadir / 'binding' / 'HookCallerPython.cpp'
    expected_hook_caller_python_file = datadir / 'ExpectedHookCallerPython.cpp'

    assert obtained_hook_specs_file.read_text() == expected_hook_specs_file.read_text()
    assert obtained_hook_caller_file.read_text() == expected_hook_caller_file.read_text()
    assert obtained_hook_caller_python_file.read_text() == expected_hook_caller_python_file.read_text()
