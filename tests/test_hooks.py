from pathlib import Path
from shutil import copy2

import pytest

from hookman.hooks import HookMan, HooksSpecs


def test_find_plugin(datadir, libs_path):
    def friction_factor(v1: 'int', v2: 'int') -> 'int':
        """
        Docs for Friction Factor
        """

    plugin_specs = HooksSpecs(project_name='acme', version='1', pyd_name='_test_hooks', hooks=[friction_factor])

    HookMan(specs=plugin_specs, plugin_dirs=[datadir])

    with pytest.raises(FileNotFoundError, match="The given path doesn't have a .yaml file"):
        HookMan(specs=plugin_specs, plugin_dirs=[Path('NON_EXISTING_PATH')])


def test_hook_specs_without_arguments():
    def method_without_arguments() -> 'float':
        """
        test_method_without_arguments
        """

    # A hook must have parameters
    with pytest.raises(TypeError, match="It's not possible to create a hook without argument"):
        specs = HooksSpecs(project_name='acme', version='1', pyd_name='_acme', hooks=[method_without_arguments])


def test_hook_specs_with_missing_type_on_argument():
    def method_with_missing_type_on_argument(a: 'int', b) -> 'float':
        """
        fail_method_with_missing_type_on_argument
        """

    # A arguments of the hook must inform the type
    with pytest.raises(TypeError, match="All hooks arguments must have the type informed"):
        specs = HooksSpecs(project_name='acme', version='1', pyd_name='_acme', hooks=[method_with_missing_type_on_argument])


def test_hook_specs_without_docs_arguments():
    def method_with_docs_missing(a: 'int') -> 'int':
        pass  # pragma: no cover


    with pytest.raises(TypeError, match="All hooks must have documentation"):
        specs = HooksSpecs(project_name='acme', version='1', pyd_name='_acme', hooks=[method_with_docs_missing])


def test_get_hook_caller(datadir, libs_path):
    import os

    # Load the hook_specs.py (inside the test folder) into plugin_specs
    hook_specs = datadir / 'hook_specs.py'
    import importlib
    spec = importlib.util.spec_from_file_location('hook_specs', hook_specs)
    plugin_specs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin_specs)

    if os.sys.platform == 'win32':
        simple_plugin_dll = libs_path / 'test_hooks.dll'
    else:
        simple_plugin_dll = libs_path / 'libtest_hooks.so'

    dst_path = datadir / 'plugin'
    copy2(src=simple_plugin_dll, dst=dst_path)

    hm = HookMan(specs=plugin_specs.specs, plugin_dirs=[datadir])
    hook_caller = hm.get_hook_caller()
    friction_factor = hook_caller.friction_factor()
    assert friction_factor(1, 2) == 3

