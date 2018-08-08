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
    hg.generate_project_files(dst_path=datadir)

    obtained_hook_specs_file = datadir / 'plugin' / 'hook_specs.h'
    expected_hook_specs_file = datadir / 'expected_hook_specs.h'

    obtained_hook_caller_file = datadir / 'cpp' / 'HookCaller.hpp'
    expected_hook_caller_file = datadir / 'ExpectedHookCaller.hpp'

    obtained_hook_caller_python_file = datadir / 'binding' / 'HookCallerPython.cpp'
    expected_hook_caller_python_file = datadir / 'ExpectedHookCallerPython.cpp'

    assert obtained_hook_specs_file.read_text() == expected_hook_specs_file.read_text()
    assert obtained_hook_caller_file.read_text() == expected_hook_caller_file.read_text()
    assert obtained_hook_caller_python_file.read_text() == expected_hook_caller_python_file.read_text()


def test_generate_plugin_template(datadir):
    plugin_dir = datadir / 'test_generate_plugin_template'
    hg = HookManGenerator(hook_spec_file_path=Path(datadir / 'hook_specs.py'))

    hg.generate_plugin_template(
        plugin_name='Acme',
        shared_lib_name='acme',
        author_name='FOO',
        author_email='FOO@FOO.com',
        dst_path=plugin_dir
    )

    obtained_hook_specs_file = datadir / 'test_generate_plugin_template/Acme/src/hook_specs.h'
    expected_hook_specs_file = datadir / 'test_generate_plugin_template/expected_hook_specs.h'

    obtained_config_yaml = datadir / 'test_generate_plugin_template/Acme/assets/config.yaml'
    expected_config_yaml = datadir / 'test_generate_plugin_template/expected_config.yaml'

    obtained_plugin_c = datadir / 'test_generate_plugin_template/Acme/src/plugin.c'
    expected_plugin_c = datadir / 'test_generate_plugin_template/expected_plugin.c'

    obtained_readme = datadir / 'test_generate_plugin_template/Acme/assets/readme.md'
    expected_readme = datadir / 'test_generate_plugin_template/expected_readme.md'

    obtained_cmake_list = datadir / 'test_generate_plugin_template/Acme/CMakeLists.txt'
    expected_cmake_list = datadir / 'test_generate_plugin_template/expected_cmakelists.txt'

    obtained_cmake_list_src = datadir / 'test_generate_plugin_template/Acme/src/CMakeLists.txt'
    expected_cmake_list_src = datadir / 'test_generate_plugin_template/expected_cmakelists_src.txt'

    obtained_build_script = datadir / 'test_generate_plugin_template/Acme/build.py'

    import sys
    if sys.platform == 'win32':
        expected_build_script = datadir / 'test_generate_plugin_template/expected_build_win32.py'
    else:
        expected_build_script = datadir / 'test_generate_plugin_template/expected_build_linux.py'

    assert obtained_hook_specs_file.read_text() == expected_hook_specs_file.read_text()
    assert obtained_config_yaml.read_text() == expected_config_yaml.read_text()
    assert obtained_plugin_c.read_text() == expected_plugin_c.read_text()
    assert obtained_readme.read_text() == expected_readme.read_text()
    assert obtained_cmake_list.read_text() == expected_cmake_list.read_text()
    assert obtained_build_script.read_text() == expected_build_script.read_text()
    assert obtained_cmake_list_src.read_text() == expected_cmake_list_src.read_text()


def test_generate_plugin_package(simple_plugin, datadir):
    plugin_path = simple_plugin['path']
    dst_plugin_dir = datadir / 'test_generate_plugin_package'
    hg = HookManGenerator(hook_spec_file_path=simple_plugin['path'].parent / 'hook_specs.py')

    hg.generate_plugin_package(
        package_name='acme',
        artifacts_dir=plugin_path,
        dst=dst_plugin_dir
    )

    compressed_plugin = dst_plugin_dir / 'acme.hmplugin'
    assert compressed_plugin.exists()

    from zipfile import ZipFile
    plugin_file_zip = ZipFile(compressed_plugin)
    list_of_files = [file.filename for file in plugin_file_zip.filelist]

    assert 'plugin.yaml' in list_of_files
    assert 'readme.md' in list_of_files

    import sys
    if sys.platform == 'win32':
        shared_lib_name = 'simple_plugin.dll'
    else:
        shared_lib_name = 'libsimple_plugin.so'

    assert shared_lib_name in list_of_files
