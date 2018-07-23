import invoke


@invoke.task
def compile(ctx):
    """
    A task to compile all dlls and pyd necessary for the tests
    """
    import os
    import shutil
    from pathlib import Path

    project_dir = Path(__file__).parent

    build_dir = project_dir / 'build'
    ninja_dir = project_dir / 'build/ninja'
    libs_dir = project_dir / 'build/libs'

    if libs_dir.exists():
        shutil.rmtree(libs_dir)
    if ninja_dir.exists():
        shutil.rmtree(ninja_dir)

    os.makedirs(libs_dir)
    os.makedirs(ninja_dir)

    import sys

    call_cmake = f'cmake -DCMAKE_BUILD_TYPE=Release -G Ninja "{build_dir}" -DHEAVY_COMPILATION_PARALLEL_JOBS=8'
    call_ninja = 'ninja -j 8'
    call_install = 'ninja install'

    with ctx.cd(str(ninja_dir)):
        if sys.platform == 'win32':
            paths = (
                os.path.expandvars(
                    r'${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvarsall.bat'),
                os.path.expandvars(
                    r'${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\BuildTools\VC\Auxiliary\Build\vcvarsall.bat'),
                os.path.expandvars(
                    r'${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\Professional\VC\Auxiliary\Build\vcvarsall.bat'),
                os.path.expandvars(
                    r'${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\WDExpress\VC\Auxiliary\Build\vcvarsall.bat'),
                    # App Veyor PROGRAMFILES not defined
                r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvars64.bat",
            )
            for msvc_path in paths:
                if os.path.isfile(msvc_path):
                    break
            else:
                raise RuntimeError(
                    "Couldn't find MSVC compiler in any of:\n{}".format('- ' + '\n- '.join(paths)))

            call_cmd = f'call "{msvc_path}" amd64'
            ctx.run(command=call_cmd + '&' + call_cmake + '&&' + call_ninja + '&&' + call_install)

        else:
            ctx.run(command=call_cmake + '&&' + call_ninja + '&&' + call_install)


@invoke.task
def generate_files(ctx):
    """
    Task to generate the files necessaries to compile the tests
    """
    import os
    from pathlib import Path
    import shutil
    from textwrap import dedent
    from hookman.hookman_generator import HookManGenerator

    project_dir = Path(__file__).parent

    test_dir = project_dir / 'tests'
    test_build_dir = project_dir / 'build/build_test'

    # Clean UP
    if test_build_dir.exists():
        shutil.rmtree(test_build_dir)
    os.makedirs(test_build_dir)

    # Finding Tests
    hook_spec_paths = [path
        for path in test_dir.glob('**/hook_specs.py')
        if 'tmp' not in path.parts
    ]

    # Root CMakeList.txt that includes all sub_directory with tests to be compile
    cmake_file_of_test_build_dir = [f'add_subdirectory({i.parent.name })\n' for i in hook_spec_paths]
    with open(test_build_dir / 'CMakeLists.txt', mode='w+') as file:
        file.writelines(cmake_file_of_test_build_dir)

    # For each hook_specs, create a directory for the compilation and generate the files
    for hook_spec_path in hook_spec_paths:
        folder_test_name = hook_spec_path.parent.name

        dir_for_compilation = test_build_dir / folder_test_name
        os.makedirs(dir_for_compilation)

        hm_generator = HookManGenerator(hook_spec_file_path=hook_spec_path)
        hm_generator.generate_files(dst_path=dir_for_compilation)

        with open(dir_for_compilation / 'CMakeLists.txt', mode='w+') as file:
            file.write(dedent("""\
                add_subdirectory(plugin)
                add_subdirectory(cpp)
                add_subdirectory(binding)
                """))

        list_with_c_files_names = [c_file for c_file in hook_spec_path.parent.glob('**/*.c')]
        for i in list_with_c_files_names:
            shutil.copy2(src=i, dst=dir_for_compilation / 'plugin')

        cmake_plugin = dir_for_compilation / 'plugin/CMakeLists.txt'
        if list_with_c_files_names:
            with open(cmake_plugin, mode='w') as file:
                file.writelines(dedent(f"""\
                        add_library({folder_test_name} SHARED {" ".join(str(x.name) for x in list_with_c_files_names)} hook_specs.h)

                        install(TARGETS {folder_test_name} EXPORT ${{PROJECT_NAME}}_export DESTINATION ${{LIBS_DIR}})
                        """
                ))
        else:
            open(cmake_plugin, mode='w+').close()


@invoke.task
def build(ctx):
    """
    A task to build all the necessary files for the test and compile the dlls and pyd;
    """
    generate_files(ctx)
    compile(ctx)
    _create_zip_files(ctx)


def _create_zip_files(ctx):
    """
    This functions can be just called when the generate_files and compile tasks have been already invoked
    """
    import os
    import shutil
    from pathlib import Path
    from zipfile import ZipFile
    project_dir = Path(__file__).parent
    libs_dir = project_dir / 'build/libs'
    plugins_zip = project_dir / 'build/plugin_zip'

    if plugins_zip.exists():
        shutil.rmtree(plugins_zip)
    os.makedirs(plugins_zip)

    # Currently the generation of zip files for test are not automatically, you must indicate
    # which plugins should be compressed in zip file.
    # TODO Look for folders inside the tests/plugins and automatically generate zip files
    for _, dirs, _ in os.walk(Path("tests/plugins/")):
        plugins_dirs = dirs
        break  # Get just the first level

    for plugin in plugins_dirs:
        plugin_yaml_path = project_dir / f"tests/plugins/{plugin}/plugin.yaml"
        plugin_readme_path = project_dir / f"tests/plugins/{plugin}/readme.md"

        if os.sys.platform == 'win32':
            shared_libs_path = libs_dir / f"{plugin}.dll"
        else:
            shared_libs_path = libs_dir / f"lib{plugin}.so"

        with ZipFile(plugins_zip / f"{plugin}.zip", 'w') as zip:
            zip.write(filename=plugin_yaml_path, arcname=plugin_yaml_path.name)
            zip.write(filename=shared_libs_path, arcname=shared_libs_path.name)
            zip.write(filename=plugin_readme_path, arcname=plugin_readme_path.name)

    # if os.sys.platform == 'win32':
    #     shared_libs_path = libs_dir / 'simple_plugin.dll'
    # else:
    #     shared_libs_path = libs_dir / 'libsimple_plugin.so'
    #
    # plugin_yaml_path = project_dir / 'tests/plugins/simple_plugin/plugin.yaml'
    #
    # with ZipFile(plugins_zip / 'simple_plugin.zip', 'w') as zip:
    #     zip.write(filename=plugin_yaml_path, arcname=plugin_yaml_path.name)
    #     zip.write(filename=shared_libs_path, arcname=shared_libs_path.name)
    #
    #
    # plugin_yaml_path = project_dir / 'tests/plugins/simple_plugin/plugin.yaml'


@invoke.task
def ci_build(ctx):
    build(ctx)
