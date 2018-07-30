import sys

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
                os.path.expandvars(r'${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvarsall.bat'),
                os.path.expandvars(r'${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\BuildTools\VC\Auxiliary\Build\vcvarsall.bat'),
                os.path.expandvars(r'${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\Professional\VC\Auxiliary\Build\vcvarsall.bat'),
                os.path.expandvars(r'${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\WDExpress\VC\Auxiliary\Build\vcvarsall.bat'),
                # On AppVeyor the variable PROGRAMFILES is not defined
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

    directory_of_the_tests = project_dir / 'tests/plugins'
    directory_to_build_tests = project_dir / 'build/build_directory_for_tests'

    # Clean UP
    if directory_to_build_tests.exists():
        shutil.rmtree(directory_to_build_tests)
    os.makedirs(directory_to_build_tests)

    # Finding hook_specs.py
    hook_spec_paths = [path
        for path in directory_of_the_tests.glob('**/hook_specs.py')
        if 'tmp' not in path.parts
    ]

    # Root CMakeList.txt that includes all sub_directory with tests to be compile
    cmake_file_of_test_build_dir = [f'add_subdirectory({i.parent.name })\n' for i in hook_spec_paths]
    with open(directory_to_build_tests / 'CMakeLists.txt', mode='w+') as file:
        file.writelines(cmake_file_of_test_build_dir)

    # For each hook_specs, create a directory for the compilation and generate the files
    for hook_spec_path in hook_spec_paths:
        project_name = hook_spec_path.parent.name

        dir_for_compilation = directory_to_build_tests / project_name
        dir_for_compilation.mkdir(parents=True)
        # os.makedirs(dir_for_compilation)

        hm_generator = HookManGenerator(hook_spec_file_path=hook_spec_path)
        hm_generator.generate_files(dst_path=dir_for_compilation)

        with open(dir_for_compilation / 'CMakeLists.txt', mode='w+') as file:
            file.write(dedent("""\
                add_subdirectory(plugin)
                add_subdirectory(cpp)
                add_subdirectory(binding)
                """))

        cmake_plugin = dir_for_compilation / 'plugin/CMakeLists.txt'
        # Find folder with Plugins
        plugins_dirs = [x for x in hook_spec_path.parent.iterdir() if x.is_dir()]

        # Identify the C Files
        for plugin in plugins_dirs:
            list_with_c_files_names = [c_file for c_file in plugin.glob('**/*.c')]

            # Copy the c files to compilation dir
            for i in list_with_c_files_names:
                shutil.copy2(src=i, dst=dir_for_compilation / 'plugin')

            # Write the plugin in a cmake file
            cmake_file_for_plugin = dir_for_compilation / 'plugin/CMakeLists.txt'
            with open(cmake_file_for_plugin, mode='a') as file:
                file.writelines(dedent(f"""\
                    add_library({plugin.name} SHARED {" ".join(str(x.name) for x in list_with_c_files_names)} hook_specs.h)

                    install(TARGETS {plugin.name} EXPORT ${{PROJECT_NAME}}_export DESTINATION ${{LIBS_DIR}})
                    """
                ))



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
    import shutil
    from pathlib import Path
    from zipfile import ZipFile
    project_dir = Path(__file__).parent
    libs_dir = project_dir / 'build/libs'
    plugins_src_dir = project_dir / "tests/plugins/"
    plugins_projects = [x for x in plugins_src_dir.iterdir() if x.is_dir()]
    plugins_zip = project_dir / 'build/plugin_zip'
    print("\n\n-- Creating Zip Files \n")

    if plugins_zip.exists():
        shutil.rmtree(plugins_zip)

    plugins_zip.mkdir(parents=True)

    for project in plugins_projects:
        plugins_dirs = [x.name for x in project.iterdir() if x.is_dir()]

        for plugin in plugins_dirs:
            plugin_yaml_path = project_dir / f"tests/plugins/{project.name}/{plugin}/plugin.yaml"
            plugin_readme_path = project_dir / f"tests/plugins/{project.name}/{plugin}/readme.md"

            if sys.platform == 'win32':
                shared_libs_path = libs_dir / f"{plugin}.dll"
            else:
                shared_libs_path = libs_dir / f"lib{plugin}.so"

            with ZipFile(plugins_zip / f"{plugin}.hmplugin", 'w') as zip_file:
                    zip_file.write(filename=plugin_yaml_path, arcname=plugin_yaml_path.name)
                    zip_file.write(filename=shared_libs_path, arcname=shared_libs_path.name)
                    zip_file.write(filename=plugin_readme_path, arcname=plugin_readme_path.name)
