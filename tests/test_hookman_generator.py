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

    obtained_plugin_yaml = datadir / 'test_generate_plugin_template/Acme/assets/plugin.yaml'
    expected_plugin_yaml = datadir / 'test_generate_plugin_template/expected_plugin.yaml'

    obtained_plugin_c = datadir / 'test_generate_plugin_template/Acme/src/plugin.c'
    expected_plugin_c = datadir / 'test_generate_plugin_template/expected_plugin.c'

    obtained_readme = datadir / 'test_generate_plugin_template/Acme/assets/README.md'
    expected_readme = datadir / 'test_generate_plugin_template/expected_readme.md'

    obtained_cmake_list = datadir / 'test_generate_plugin_template/Acme/CMakeLists.txt'
    expected_cmake_list = datadir / 'test_generate_plugin_template/expected_cmakelists.txt'

    obtained_cmake_list_src = datadir / 'test_generate_plugin_template/Acme/src/CMakeLists.txt'
    expected_cmake_list_src = datadir / 'test_generate_plugin_template/expected_cmakelists_src.txt'

    obtained_compile_script = datadir / 'test_generate_plugin_template/Acme/compile.py'
    expected_compile_script = datadir / 'test_generate_plugin_template/expected_compile.py'

    assert obtained_hook_specs_file.read_text() == expected_hook_specs_file.read_text()
    assert obtained_plugin_yaml.read_text() == expected_plugin_yaml.read_text()
    assert obtained_plugin_c.read_text() == expected_plugin_c.read_text()
    assert obtained_readme.read_text() == expected_readme.read_text()
    assert obtained_cmake_list.read_text() == expected_cmake_list.read_text()
    assert obtained_compile_script.read_text() == expected_compile_script.read_text()
    assert obtained_cmake_list_src.read_text() == expected_cmake_list_src.read_text()


def test_generate_plugin_package(simple_plugin, acme_hook_specs_file, tmpdir):
    hg = HookManGenerator(hook_spec_file_path=acme_hook_specs_file)

    hg.generate_plugin_template(
        plugin_name='acme',
        shared_lib_name='acme',
        author_email='acme1',
        author_name='acme2',
        dst_path=Path(tmpdir)
    )
    plugin_dir = Path(tmpdir) / 'acme'

    artifacts_dir = plugin_dir / 'artifacts'
    artifacts_dir.mkdir()
    import sys

    if sys.platform == 'win32':
        shared_lib_name = 'acme.dll'
        hm_plugin_name = 'acme-win64.hmplugin'
    else:
        shared_lib_name = 'libacme.so'
        hm_plugin_name = 'acme-linux64.hmplugin'

    test_dll = artifacts_dir / shared_lib_name
    test_dll.write_text('')

    hg.generate_plugin_package(
        package_name='acme',
        plugin_dir=plugin_dir,
    )

    compressed_plugin = plugin_dir / hm_plugin_name
    assert compressed_plugin.exists()

    from zipfile import ZipFile
    plugin_file_zip = ZipFile(compressed_plugin)
    list_of_files = [file.filename for file in plugin_file_zip.filelist]

    assert 'assets/plugin.yaml' in list_of_files
    assert 'assets/README.md' in list_of_files
    assert f'artifacts/{shared_lib_name}' in list_of_files


def test_generate_plugin_package_with_missing_folders(simple_plugin, acme_hook_specs_file, tmpdir):
    import sys
    from textwrap import dedent
    from hookman.exceptions import AssetsDirNotFoundError, ArtifactsDirNotFoundError, SharedLibraryNotFoundError
    hg = HookManGenerator(hook_spec_file_path=acme_hook_specs_file)
    plugin_dir = Path(tmpdir) / 'acme'
    plugin_dir.mkdir()

    # -- Without Assets Folder
    with pytest.raises(AssetsDirNotFoundError):
        hg.generate_plugin_package(package_name='acme', plugin_dir=plugin_dir)

    asset_dir = plugin_dir / 'assets'
    asset_dir.mkdir()

    # -- Without Artifacts Folder
    with pytest.raises(ArtifactsDirNotFoundError):
        hg.generate_plugin_package(package_name='acme', plugin_dir=plugin_dir)

    artifacts_dir = plugin_dir / 'artifacts'
    artifacts_dir.mkdir()

    # -- Without a shared library binary
    shared_lib = '*.dll' if sys.platform == 'win32' else '*.so'
    string_to_match = f'Unable to locate a shared library \(\{shared_lib}\) in'
    with pytest.raises(FileNotFoundError, match=string_to_match):
        hg.generate_plugin_package(package_name='acme', plugin_dir=plugin_dir)

    lib_name = 'test.dll' if sys.platform == 'win32' else 'libtest.so'
    shared_library_file = artifacts_dir / lib_name
    shared_library_file.write_text('')

    # -- Without Config file
    with pytest.raises(FileNotFoundError, match=f'Unable to locate the file plugin.yaml in'):
        hg.generate_plugin_package(package_name='acme', plugin_dir=plugin_dir)

    config_file = asset_dir / 'plugin.yaml'
    config_file.write_text(dedent(f"""\
            plugin_name: 'ACME'
            plugin_version: '1'

            author: 'acme_author'
            email: 'acme_email'

            shared_lib: 'acme'
        """))
    # -- Without Readme file
    with pytest.raises(FileNotFoundError, match=f'Unable to locate the file README.md in'):
        hg.generate_plugin_package(package_name='acme', plugin_dir=plugin_dir)

    readme_file = asset_dir / 'README.md'
    readme_file.write_text('')

    # # -- With a invalid shared_library name on config_file
    if sys.platform == 'win32':
        acme_lib_name = 'acme.dll'
        hm_plugin_name = 'acme-win64.hmplugin'
    else:
        acme_lib_name = 'libacme.so'
        hm_plugin_name = 'acme-linux64.hmplugin'

    with pytest.raises(SharedLibraryNotFoundError, match=f'{acme_lib_name} could not be found'):
        hg.generate_plugin_package(package_name='acme', plugin_dir=plugin_dir)

    acme_shared_library_file = artifacts_dir / acme_lib_name
    acme_shared_library_file.write_text('')

    hg.generate_plugin_package(package_name='acme', plugin_dir=plugin_dir)
    compressed_plugin_package = plugin_dir / hm_plugin_name
    assert compressed_plugin_package.exists()
