import os
import shutil
import sys
from pathlib import Path

import invoke

from hookman.hookman_generator import HookManGenerator


@invoke.task
def build(ctx):
    """
    A task to build all the necessary files for the test and compile the dlls and pyd;
    """
    generate_build_files(ctx)
    compile_build_files(ctx)
    _package_plugins(ctx)


@invoke.task
def generate_build_files(ctx):
    """
    Task to generate the files necessaries to compile the tests
    """

    project_dir = Path(__file__).parent

    directory_of_the_tests = project_dir / "tests/plugins"
    directory_to_build_tests = project_dir / "build/build_directory_for_tests"

    # Clean UP
    if directory_to_build_tests.exists():
        shutil.rmtree(directory_to_build_tests)
    os.makedirs(directory_to_build_tests)

    # Finding hook_specs.py, each hook_specs represent a different project with different hooks
    hook_spec_paths = [
        path for path in directory_of_the_tests.glob("**/hook_specs.py") if "tmp" not in path.parts
    ]

    # CMakeList.txt that includes all sub_directory with tests to be compiled
    root_cmake_list = directory_to_build_tests / "CMakeLists.txt"
    cmake_file_of_test_build_dir = [
        f"add_subdirectory({i.parent.name })\n" for i in hook_spec_paths
    ]
    root_cmake_list.write_text("".join(cmake_file_of_test_build_dir))

    # For each hook_specs, create a directory for the compilation and generate the files
    for project_hook_spec_path in hook_spec_paths:
        project_dir_for_build = directory_to_build_tests / project_hook_spec_path.parent.name
        project_dir_for_build.mkdir(parents=True)

        hm_generator = HookManGenerator(hook_spec_file_path=project_hook_spec_path)
        hm_generator.generate_project_files(dst_path=project_dir_for_build)

        # Find folder with Plugins
        plugins_dirs = [
            x
            for x in project_hook_spec_path.parent.iterdir()
            if x.is_dir() and (x / "assets").exists()
        ]

        # Copy all the plugins to the build dir
        for plugin in plugins_dirs:
            plugin_dir_build = project_dir_for_build / f"plugin/{plugin.name}"
            shutil.copytree(src=plugin, dst=plugin_dir_build)
            (plugin_dir_build / "src/hook_specs.h").write_text(
                hm_generator._hook_specs_header_content(plugin.stem)
            )

        # Create the CMakeFile on root of the project to include others CMake files.
        main_cmakelist = project_dir_for_build / "CMakeLists.txt"
        main_cmakelist_content = []
        main_cmakelist_content.append("add_subdirectory(cpp)\nadd_subdirectory(binding)\n")
        main_cmakelist_content += [
            f"add_subdirectory(plugin/{plugin.name}/src)\n" for plugin in plugins_dirs
        ]
        main_cmakelist.write_text("".join(main_cmakelist_content))


@invoke.task
def compile_build_files(ctx):
    """
    A task to compile all dlls and pyd necessary for the tests
    """
    project_dir = Path(__file__).parent

    build_dir = project_dir / "build"
    ninja_dir = project_dir / "build/ninja"
    artifacts_dir = project_dir / "build/artifacts"

    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    if ninja_dir.exists():
        shutil.rmtree(ninja_dir)

    os.makedirs(artifacts_dir)
    os.makedirs(ninja_dir)

    call_cmake = (
        f"cmake "
        f"-DCMAKE_BUILD_TYPE=Release "
        f'-G Ninja "{build_dir}" '
        f"-DPYTHON_EXECUTABLE={sys.executable} "
    )
    call_ninja = "ninja -j 8"
    call_install = "ninja install"

    with ctx.cd(str(project_dir / "build/ninja")):
        if sys.platform == "win32":
            paths = (
                os.path.expandvars(
                    r"${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvarsall.bat"
                ),
                os.path.expandvars(
                    r"${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
                ),
                os.path.expandvars(
                    r"${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\Professional\VC\Auxiliary\Build\vcvarsall.bat"
                ),
                os.path.expandvars(
                    r"${PROGRAMFILES(X86)}\Microsoft Visual Studio\2017\WDExpress\VC\Auxiliary\Build\vcvarsall.bat"
                ),
                # Path for vcvars on GithubAction
                r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat",
            )
            for msvc_path in paths:
                if os.path.isfile(msvc_path):
                    break
            else:
                raise RuntimeError(
                    "Couldn't find MSVC compiler in any of:\n{}".format("- " + "\n- ".join(paths))
                )

            call_cmd = f'call "{msvc_path}" amd64'
            ctx.run(command=call_cmd + "&" + call_cmake + "&&" + call_ninja + "&&" + call_install)

        else:
            ctx.run(command=call_cmake + "&&" + call_ninja + "&&" + call_install)


def _package_plugins(ctx):
    """
    This functions can be just called when the generate_project_files and compile tasks have been already invoked
    """
    print("\n\n-- Creating Zip Files \n")

    project_dir = Path(__file__).parent
    plugins_projects = [
        x for x in (project_dir / "build/build_directory_for_tests/").iterdir() if x.is_dir()
    ]
    artifacts_dir = project_dir / "build/artifacts"

    plugins_zip = project_dir / "build/plugin_zip"
    if plugins_zip.exists():
        shutil.rmtree(plugins_zip)

    plugins_zip.mkdir()

    for project in plugins_projects:
        plugins_dirs = [
            x for x in (project / "plugin").iterdir() if x.is_dir() and (x / "assets").exists()
        ]
        hm_generator = HookManGenerator(
            hook_spec_file_path=project_dir / f"tests/plugins/{project.name}/hook_specs.py"
        )

        for plugin in plugins_dirs:
            (plugin / "artifacts").mkdir()
            if sys.platform == "win32":
                shutil.copy2(src=artifacts_dir / f"{plugin.name}.dll", dst=plugin / "artifacts")
            else:
                shutil.copy2(src=artifacts_dir / f"lib{plugin.name}.so", dst=plugin / "artifacts")

            hm_generator.generate_plugin_package(
                package_name=plugin.name, plugin_dir=plugin, dst_path=plugins_zip
            )
