from pathlib import Path
from shutil import copy2

import pytest

from hookman.hooks import HookMan, HooksSpecs



@pytest.fixture()
def plugin_specs():
    """
    This plugin specs has the same interface as the simple_plugin
    """

    def friction_factor(v1: 'int', v2: 'int') -> 'int':
        """
        Docs for Friction Factor
        """

    return HooksSpecs(project_name='acme', version='4', pyd_name='_test_hooks', hooks=[friction_factor])


def test_find_plugin(datadir, libs_path, plugin_specs):

    HookMan(specs=plugin_specs, plugin_dirs=[datadir])

    with pytest.raises(FileNotFoundError, match="The given path doesn't have a .yaml file"):
        HookMan(specs=plugin_specs, plugin_dirs=[Path('NON_EXISTING_PATH')])


def test_check_hook_arguments():

    def test_method_without_arguments() -> 'float':
        """
        test_method_without_arguments
        """
        pass

    def fail_method_with_missing_type_on_argument(a: 'int', b) -> 'float':
        """
        fail_method_with_missing_type_on_argument
        """
        pass

    def fail_method_with_docs_missing(a: 'int') -> 'int':
        pass

    # A hook must have parameters
    with pytest.raises(TypeError, match="It's not possible to create a hook without argument"):
        specs = HooksSpecs(project_name='acme', version='1', pyd_name='_acme', hooks=[test_method_without_arguments])

    # A arguments of the hook must inform the type
    with pytest.raises(TypeError, match="All hooks arguments must have the type informed"):
        specs = HooksSpecs(project_name='acme', version='1', pyd_name='_acme', hooks=[fail_method_with_missing_type_on_argument])

    with pytest.raises(TypeError, match="All hooks must have documentation"):
        specs = HooksSpecs(project_name='acme', version='1', pyd_name='_acme', hooks=[fail_method_with_docs_missing])


def test_get_hook_caller(datadir, libs_path, plugin_specs):
    simple_plugin_dll = libs_path / 'test_hooks.dll'
    dst_path = datadir / 'plugin'
    copy2(src=simple_plugin_dll, dst=dst_path)

    hm = HookMan(specs=plugin_specs, plugin_dirs=[datadir])
    hookCaller = hm.get_hook_caller()
