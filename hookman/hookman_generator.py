import importlib
import inspect
import os
import re
import sys
from pathlib import Path
from textwrap import dedent
from typing import NamedTuple
from zipfile import ZipFile

from hookman.exceptions import (
    ArtifactsDirNotFoundError, AssetsDirNotFoundError, HookmanError, SharedLibraryNotFoundError)
from hookman.hooks import HookSpecs
from hookman.plugin_config import PluginInfo

INDENTATION = "    "
NEW_LINE = "\n"


class Hook(NamedTuple):
    """
    Class to assist on the process to generate the files

    args: The name of each argument
        Ex.: v1, v2, v3

    args_type: The type of each argument
        Ex.: int, float, int

    args_with_type: The name of the argument with the type
        Ex.: int v1, float v2, int v3

    documentation: The docstring content from the hook definition

    function_name: Full name of the hook function
        Ex.: project_name_version_hook_name -> alfasim_v4_friction_factory

    macro_name: Name of the Hook in Upper Case

    name: Name of the Hook

    r_type: Type of the return from the hook


    """
    args: str
    args_type: str
    args_with_type: str
    documentation: str
    function_name: str
    macro_name: str
    name: str
    r_type: str


class HookManGenerator:
    """
    Class to assist in the process of creating necessary files for the hookman
    """

    def __init__(self, hook_spec_file_path: Path) -> None:
        """
        Receives a path to a hooks specification file.
        if the Path provided is not a file an exception FileNotFoundError is raised.
        If the File provided doesn't have a spec object, a RuntimeError is raised.
        """
        if hook_spec_file_path.is_file():
            hook_spec_module = self._import_hook_specification_file(hook_spec_file_path)
            self._populate_local_variables(hook_spec_module.specs)
        else:
            raise FileNotFoundError(f"File not found: {hook_spec_file_path}")

    def _import_hook_specification_file(self, hook_spec_file_path: Path) -> HookSpecs:
        """
        Returns the "HookSpecs" object that defines the hook specification provide from the project.
        The file is considered valid if the importlib can access the object called "specs"

        :param hook_spec_file_path: Path to the location of the file
        :return: A Python module that represent specification from the given file
        """
        spec = importlib.util.spec_from_file_location('hook_specs', hook_spec_file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            getattr(module, 'specs')
        except AttributeError:
            raise RuntimeError("Invalid file, specs not defined.")

        return module

    def _populate_local_variables(self, hook_specs: HookSpecs):
        """
        Populate the self.hooks property with the given hook specification.
        See the docstring from the Hook type for more details about the self.hooks
        """
        self.project_name = hook_specs.project_name.lower()
        self.pyd_name = hook_specs.pyd_name
        self.version = f'v{hook_specs.version}'

        def get_arg_with_type(arg):
            arg_type = hook_types[arg]
            array_type_pattern = (
                r'(?P<array_type>.+)'  # `double ` in `double [ 2 ]`
                r'(?:\s*\[\s*'  # `[` and possible spaces
                    r'(?P<array_size>\d*)'  # `2` in `double [ 2 ]` or empty in `int[]`
                r'\s*\]\s*)$'  # `]` with possible spaces and end of string
            )
            m = re.match(array_type_pattern, arg_type)
            if m is not None:
                array_type = m.group('array_type').strip()
                array_size = m.group('array_size')
                return f"{array_type} {arg}[{array_size}]"
            return f"{arg_type.strip()} {arg}"

        self.extra_includes = hook_specs.extra_includes
        self.hooks = []
        for hook_spec in hook_specs.hooks:
            hook_documentation = inspect.getdoc(hook_spec)
            hook_arg_spec = inspect.getfullargspec(hook_spec)
            hook_arguments = hook_arg_spec.args
            hook_types = hook_arg_spec.annotations
            self.hooks.append(
                Hook(
                    args=', '.join(hook_arguments),
                    args_type=', '.join([f"{hook_types[arg]}" for arg in hook_arguments]),
                    args_with_type=', '.join(get_arg_with_type(arg) for arg in hook_arguments),
                    documentation=hook_documentation,
                    function_name=f'{self.project_name}_{self.version}_{hook_spec.__name__.lower()}',
                    macro_name=hook_spec.__name__.upper(),
                    name=hook_spec.__name__.lower(),
                    r_type=hook_arg_spec.annotations['return'],
                ))

    def generate_plugin_template(self,
            plugin_name: str,
            shared_lib_name: str,
            author_email: str,
            author_name: str,
            dst_path: Path):
        """
        Generate a template with the necessary files and structure to create a plugin

        A folder with the same name as the shared_lib_name argument will be created, with the following files:
            <plugin_folder>
                - CMakeLists.txt
                - compile.py
                assets/
                    - plugin.yaml
                    - README.md
                src/
                    - hook_specs.h
                    - plugin.c
                    - CMakeLists.txt
        """
        if not shared_lib_name.isidentifier():
            raise HookmanError("The shared library name must be a valid identifier.")

        plugin_folder = dst_path / shared_lib_name
        assets_folder = plugin_folder / 'assets'
        source_folder = plugin_folder / 'src'

        if not plugin_folder.exists():
            plugin_folder.mkdir(parents=True)

        if not assets_folder.exists():
            assets_folder.mkdir()

        if not source_folder.exists():
            source_folder.mkdir()

        Path(plugin_folder / 'compile.py').write_text(self._compile_shared_lib_python_script_content(shared_lib_name))
        Path(plugin_folder / 'CMakeLists.txt').write_text(self._plugin_cmake_file_content(shared_lib_name))
        Path(assets_folder / 'plugin.yaml').write_text(self._plugin_config_file_content(plugin_name, shared_lib_name, author_email, author_name))
        Path(assets_folder / 'README.md').write_text(self._readme_content(plugin_name, author_email, author_name))
        Path(source_folder / 'hook_specs.h').write_text(self._hook_specs_header_content(shared_lib_name))
        Path(source_folder / 'plugin.c').write_text(self._plugin_source_content())
        Path(source_folder / 'CMakeLists.txt').write_text(self._plugin_src_cmake_file_content(shared_lib_name))

    def generate_project_files(self, dst_path: Path):
        """
        Generate the following files on the dst_path:
        - HookCaller.hpp
        - HookCallerPython.cpp
        """
        hook_caller_hpp = Path(dst_path / 'cpp' / 'HookCaller.hpp')
        hook_caller_python = Path(dst_path / 'binding' / 'HookCallerPython.cpp')

        os.makedirs(hook_caller_hpp.parent)
        os.makedirs(hook_caller_python.parent)

        hook_caller_hpp.write_text(self._hook_caller_hpp_content())
        hook_caller_python.write_text(self._hook_caller_python_content())

        self._generate_cmake_files(dst_path)

    def generate_plugin_package(self, package_name: str, plugin_dir: Path, dst: Path=None):
        """
        Creates a .hmplugin file using the name provided on package_name argument.
        The file `.hmplugin` will be created with the content from the folder assets and artifacts.

        In order to successfully creates a plugin, at least the following files should be present:
            - plugin.yml
            - shared library (.ddl or .so)
            - readme.md

        Per default, the package will be created inside the folder plugin_dir, however it's possible
        to give another path filling the dst argument
        """
        if dst is None:
            dst = plugin_dir

        assets_dir = plugin_dir / "assets"
        artifacts_dir = plugin_dir / "artifacts"
        python_dir = plugin_dir / "src" / "python"

        self._validate_package_folder(artifacts_dir, assets_dir)
        self._validate_plugin_config_file(assets_dir / 'plugin.yaml', artifacts_dir)

        if sys.platform == 'win32':
            shared_lib = '*.dll'
            hmplugin_path = dst / f"{package_name}-win64.hmplugin"
        else:
            shared_lib = '*.so'
            hmplugin_path = dst / f"{package_name}-linux64.hmplugin"

        with ZipFile(hmplugin_path, 'w') as zip_file:
            for file in assets_dir.rglob('*'):
                zip_file.write(filename=file, arcname=file.relative_to(plugin_dir))

            for file in artifacts_dir.rglob(shared_lib):
                zip_file.write(filename=file, arcname=file.relative_to(plugin_dir))

            for file in python_dir.rglob('*'):
                dst_filename = Path('artifacts' / file.relative_to(plugin_dir / 'src/python'))
                zip_file.write(filename=file, arcname=dst_filename)

    def _validate_package_folder(self, artifacts_dir, assets_dir):
        """
        Method to ensure that the plugin folder has the following criteria:
            - An "assets" folder should be present
            - An "artifacts" folder should be present

            - The assets folder needs to contain:
                - Readme.md
                - plugin.yaml

            - The artifacts folder need to contain:
                - At least one shared library (.dll or .so)

            - The plugin.yaml should have the name of the main library in the "shared_lib" entry.
        """
        if not assets_dir.exists():
            raise AssetsDirNotFoundError()

        if not artifacts_dir.exists():
            raise ArtifactsDirNotFoundError()

        shared_lib = '*.dll' if sys.platform == 'win32' else '*.so'
        if not any(artifacts_dir.rglob(shared_lib)):
            raise FileNotFoundError(
                f"Unable to locate a shared library ({shared_lib}) in {artifacts_dir}")

        if not assets_dir.joinpath('plugin.yaml').is_file():
            raise FileNotFoundError(f"Unable to locate the file plugin.yaml in {assets_dir}")

        if not assets_dir.joinpath('README.md').is_file():
            raise FileNotFoundError(f"Unable to locate the file README.md in {assets_dir}")

    def _validate_plugin_config_file(cls, plugin_config_file: Path, artifacts_dir: Path):
        """
        Check if the given plugin_file is valid,
        currently the only check that this method do is to verify if the shared_lib is available
        """
        plugin_file_content = PluginInfo(plugin_config_file, hooks_available=None)

        if not artifacts_dir.joinpath(plugin_file_content.shared_lib_name).is_file():
            raise SharedLibraryNotFoundError(
                f"{plugin_file_content.shared_lib_name} could not be found in {artifacts_dir}"
            )

    def _hook_specs_header_content(self, shared_lib_name) -> str:
        """
        Create a C header file with the content informed on the hook_specs
        """
        file_content = ''
        list_with_hook_specs_with_documentation = ''

        for hook in self.hooks:
            hook_specs_content = '\n/*!\n'
            hook_specs_content += hook.documentation
            hook_specs_content += dedent(f"""
            */
            #define HOOK_{hook.macro_name}({hook.args}) HOOKMAN_API_EXP {hook.r_type} HOOKMAN_FUNC_EXP {hook.function_name}({hook.args_with_type})
            """)
            list_with_hook_specs_with_documentation += hook_specs_content

        file_content += dedent(f"""\
        #ifndef {self.project_name.upper()}_HOOK_SPECS_HEADER_FILE
        #define {self.project_name.upper()}_HOOK_SPECS_HEADER_FILE
        #ifdef WIN32
            #define HOOKMAN_API_EXP __declspec(dllexport)
            #define HOOKMAN_FUNC_EXP __cdecl
        #else
            #define HOOKMAN_API_EXP
            #define HOOKMAN_FUNC_EXP
        #endif

        #define INIT_HOOKS() HOOKMAN_API_EXP const char* HOOKMAN_FUNC_EXP {self.project_name}_version_api() {{return \"{self.version}\";}}
        HOOKMAN_API_EXP const char* HOOKMAN_FUNC_EXP get_plugin_name() {{return \"{shared_lib_name}\";}}

        """)
        file_content += list_with_hook_specs_with_documentation
        file_content += dedent(f"""
        #endif
        """)
        return file_content

    def _hook_caller_hpp_content(self) -> str:
        """
        Create a .hpp file with the content informed on the hook_specs
        """
        content_lines = []
        list_with_hook_calls = []
        list_with_set_functions = []
        list_with_private_members = []

        content_lines += [
            "#ifndef _H_HOOKMAN_HOOK_CALLER",
            "#define _H_HOOKMAN_HOOK_CALLER",
            "",
            "#include <functional>",
            "#include <vector>",
            "",
        ]
        content_lines += (f'#include <{x}>' for x in self.extra_includes)
        content_lines += [
            "",
            "namespace hookman {",
            "",
            "template <typename F_TYPE> std::function<F_TYPE> from_c_pointer(uintptr_t p) {",
            f"{INDENTATION}return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));",
            "}",
            "",    
            "class HookCaller {",
            "public:",
        ]

        for hook in self.hooks:
            list_with_hook_calls += [
                f'{INDENTATION}std::vector<std::function<{hook.r_type}({hook.args_type})>> {hook.name}_impls() {{',
                f'{INDENTATION*2}return this->_{hook.name}_impls;',
                f'{INDENTATION}}}',
            ]
            list_with_private_members += [
                f'{INDENTATION}std::vector<std::function<{hook.r_type}({hook.args_type})>> _{hook.name}_impls;'
            ]

            list_with_set_functions += [
                f'{1*INDENTATION}void append_{hook.name}_impl(uintptr_t pointer) {{',
                f'{2*INDENTATION}this->_{hook.name}_impls.push_back(from_c_pointer<{hook.r_type}({hook.args_type})>(pointer));',
                f'{1*INDENTATION}}}',
                "",
            ]
        content_lines += list_with_hook_calls
        content_lines.append("")
        content_lines += list_with_set_functions
        content_lines.append("private:")
        content_lines += list_with_private_members
        content_lines.append("};")
        content_lines.append("")
        content_lines.append("}  // namespace hookman")
        content_lines.append("#endif // _H_HOOKMAN_HOOK_CALLER")
        content_lines.append('')

        return NEW_LINE.join(content_lines)

    def _hook_caller_python_content(self) -> str:
        """
        Create a .cpp file to bind python and cpp code with PyBind11
        """
        content_lines = [
            "#include <pybind11/functional.h>",
            "#include <pybind11/pybind11.h>",
            "#include <pybind11/stl_bind.h>",
            "#include <HookCaller.hpp>",
            "",
            "namespace py = pybind11;",
            "",
        ]
        signatures = set((x.r_type, x.args_type) for x in self.hooks)
        for r_type, args_type in sorted(signatures):
            content_lines.append(f"PYBIND11_MAKE_OPAQUE(std::vector<std::function<{r_type}({args_type})>>);")
        content_lines.append("")

        content_lines.append(f"PYBIND11_MODULE({self.pyd_name}, m) {{")

        for index, (r_type, args_type) in enumerate(sorted(signatures)):
            name = f'vector_hook_impl_type_{index}'
            vector_type = f"std::vector<std::function<{r_type}({args_type})>>"
            content_lines.append(f'{INDENTATION}py::bind_vector<{vector_type}>(m, "{name}");')
        content_lines.append("")

        content_lines += [
            f'{INDENTATION}py::class_<hookman::HookCaller>(m, "HookCaller")',
            f"{INDENTATION * 2}.def(py::init<>())",
        ]
        for hook in self.hooks:
            content_lines += [
                f'{2*INDENTATION}.def("{hook.name}_impls", &hookman::HookCaller::{hook.name}_impls)',
                f'{2*INDENTATION}.def("append_{hook.name}_impl", &hookman::HookCaller::append_{hook.name}_impl)',
            ]
        content_lines.append(f'{INDENTATION};')
        content_lines.append('}')
        content_lines.append('')
        return NEW_LINE.join(content_lines)

    def _generate_cmake_files(self, dst_path: Path):
        hook_caller_hpp = Path(dst_path / 'cpp' / 'CMakeLists.txt')
        hook_caller_python = Path(dst_path / 'binding' / 'CMakeLists.txt')
        from textwrap import dedent

        with open(hook_caller_hpp, mode='w') as file:
            file.writelines(dedent(f"""\
                add_library({self.pyd_name}_interface INTERFACE)
                target_include_directories({self.pyd_name}_interface INTERFACE ./)
                """))

        with open(hook_caller_python, mode='w') as file:
            file.writelines(dedent(f"""\
            include(pybind11Config)

            pybind11_add_module(
                {self.pyd_name}
                    HookCallerPython.cpp
            )
            target_include_directories(
               {self.pyd_name}
                PRIVATE
                    ${{pybind11_INCLUDE_DIRS}}  # from pybind11Config
            )
            target_link_libraries(
                {self.pyd_name}
                PRIVATE
                    {self.pyd_name}_interface
            )

            install(TARGETS {self.pyd_name} EXPORT ${{PROJECT_NAME}}_export DESTINATION ${{ARTIFACTS_DIR}})
            """))

    def _plugin_config_file_content(
            self,
            plugin_name: str,
            shared_lib_name: str,
            author_email: str,
            author_name: str,
        ) -> str:
        """
        Return a string that represent the content of a valid configuration for a plugin
        """
        file_content = dedent(f"""\
        plugin_name: '{plugin_name}'
        plugin_version: '1'
        author: '{author_name}'
        email: '{author_email}'
        shared_lib: '{shared_lib_name}'
        """)
        return file_content

    def _readme_content(self, plugin_name: str, author_email: str, author_name: str) -> str:
        file_content = dedent(f"""\
        Plugin: '{plugin_name}'
        Author: '{author_name}'
        Email: '{author_email}'

        This is a sample readme file with the supported syntax, the content of this file should be write in markdown.

        You can find an overview of the valid tags that can be used to write the content of this file on the following link:
        https://guides.github.com/features/mastering-markdown/#syntax
        """)
        return file_content

    def _plugin_source_content(self) -> str:
        """
        Create a C header file with the content informed on the hook_specs
        """
        file_content = []
        plugin_hooks_macro = [f'// HOOK_{hook.macro_name}({hook.args}){{}}{NEW_LINE}' for hook in self.hooks]

        file_content += dedent(f"""\
        #include "hook_specs.h"

        INIT_HOOKS()

        """)
        file_content += plugin_hooks_macro
        return ''.join(file_content)

    def _plugin_cmake_file_content(self, shared_lib_name):
        file_content = dedent(f'''\
            cmake_minimum_required(VERSION 3.5.2)

            set(PROJECT_NAME {shared_lib_name})
            set(ARTIFACTS_DIR ${{CMAKE_CURRENT_SOURCE_DIR}}/artifacts)

            if(NOT WIN32)
              set(CMAKE_C_COMPILER    clang)
              set(CMAKE_CXX_COMPILER  clang++)
              set(CMAKE_C_FLAGS       "-Wall -std=c99")
              set(CMAKE_C_FLAGS_DEBUG "-g")
            endif(NOT WIN32)

            set(CMAKE_CXX_LINK_FLAGS  "-lstdc++")
            set(CMAKE_CXX_FLAGS_DEBUG "-g")

            set(CMAKE_C_STANDARD 99)

            project ({shared_lib_name} LANGUAGES CXX C)
            add_subdirectory(src)
        ''')
        return file_content

    def _plugin_src_cmake_file_content(self, shared_lib_name):
        file_content = dedent(f'''\
            add_library({shared_lib_name} SHARED plugin.c hook_specs.h)
            install(TARGETS {shared_lib_name} EXPORT ${{PROJECT_NAME}}_export DESTINATION ${{ARTIFACTS_DIR}})
        ''')
        return file_content

    def _compile_shared_lib_python_script_content(self, shared_lib_name):
        lib_name_win = f"{shared_lib_name}.dll"
        lib_name_linux = f"lib{shared_lib_name}.so"

        file_content = dedent(f'''\
            import os
            import shutil
            import subprocess
            import sys
            from pathlib import Path

            current_dir = Path(os.getcwd())

            artifacts_dir = current_dir / "artifacts"
            assets = current_dir / "assets"
            build_dir = current_dir / "build"
            package_dir = current_dir / "package"

            if sys.platform == 'win32':
                shared_lib = artifacts_dir / "{lib_name_win}"
            else:
                shared_lib = artifacts_dir / "{lib_name_linux}"

            if build_dir.exists():
                shutil.rmtree(build_dir)

            build_dir.mkdir()

            binary_directory_path = f"-B{{str(build_dir)}}"
            home_directory_path = f"-H{{current_dir}}"

            build_generator = "Visual Studio 14 2015 Win64" if sys.platform == "win32" else "Unix Makefiles"
            if artifacts_dir.exists():
                shutil.rmtree(artifacts_dir)

            subprocess.check_call(["cmake", binary_directory_path, home_directory_path, "-G", build_generator])
            subprocess.check_call(["cmake", "--build", str(build_dir), "--config", "Release", "--target", "install"])

            if package_dir.exists():
                shutil.rmtree(package_dir)

            shutil.copytree(src=assets, dst=package_dir)
            shutil.copy2(src=shared_lib, dst=package_dir)
        ''')
        return file_content
