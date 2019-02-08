import importlib
import inspect
import os
import re
import sys
from pathlib import Path
from textwrap import dedent
from typing import NamedTuple, Union
from zipfile import ZipFile

from hookman.exceptions import (
    ArtifactsDirNotFoundError, AssetsDirNotFoundError, HookmanError, SharedLibraryNotFoundError)
from hookman.hooks import HookSpecs
from hookman.plugin_config import PluginInfo


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

    def __init__(self, hook_spec_file_path: Union[Path, str]) -> None:
        """
        Receives a path to a hooks specification file.
        if the Path provided is not a file an exception FileNotFoundError is raised.
        If the File provided doesn't have a spec object, a RuntimeError is raised.
        """
        hook_spec_file_path = Path(hook_spec_file_path)
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

        :param str plugin_name: the user-friendly name of the plugin, for example ``"Hydrates"``.

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

    def generate_hook_specs_header(self, shared_lib_name: str, dst_path: Union[str, Path]):
        """Generates the "hook_specs.h" file which is consumed by plugins to implement the hooks.

        :param shared_lib_name: short name of the generated shared library
        :param dst_path: directory where to generate the file.
        """
        source_folder = Path(dst_path) / shared_lib_name / 'src'
        source_folder.mkdir(parents=True, exist_ok=True)
        Path(source_folder / 'hook_specs.h').write_text(self._hook_specs_header_content(shared_lib_name))


    def generate_project_files(self, dst_path: Union[Path, str]):
        """
        Generate the following files on the dst_path:
        - HookCaller.hpp
        - HookCallerPython.cpp
        """
        hook_caller_hpp = Path(dst_path) / 'cpp' / 'HookCaller.hpp'
        hook_caller_hpp.parent.mkdir(exist_ok=True, parents=True)
        hook_caller_hpp.write_text(self._hook_caller_hpp_content())

        if self.pyd_name:
            hook_caller_python = Path(dst_path / 'binding' / 'HookCallerPython.cpp')
            hook_caller_python.parent.mkdir(exist_ok=True, parents=True)
            hook_caller_python.write_text(self._hook_caller_python_content())

        self._generate_cmake_files(dst_path)

    def generate_plugin_package(self, package_name: str, plugin_dir: Union[Path, str], dst_path: Path=None):
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
        plugin_dir = Path(plugin_dir)
        if dst_path is None:
            dst_path = plugin_dir

        assets_dir = plugin_dir / "assets"
        artifacts_dir = plugin_dir / "artifacts"
        python_dir = plugin_dir / "src" / "python"

        self._validate_package_folder(artifacts_dir, assets_dir)
        self._validate_plugin_config_file(assets_dir / 'plugin.yaml', artifacts_dir)

        if sys.platform == 'win32':
            shared_lib = '*.dll'
            hmplugin_path = dst_path / f"{package_name}-win64.hmplugin"
        else:
            shared_lib = '*.so'
            hmplugin_path = dst_path / f"{package_name}-linux64.hmplugin"

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
            raise ArtifactsDirNotFoundError(f'Artifacts directory not found: {artifacts_dir}')

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
        list_with_hook_specs_with_documentation = ''

        for hook in self.hooks:
            hook_specs_content = '\n/*!\n'
            hook_specs_content += hook.documentation
            hook_specs_content += dedent(f"""
            */
            #define HOOK_{hook.macro_name}({hook.args}) HOOKMAN_API_EXP {hook.r_type} HOOKMAN_FUNC_EXP {hook.function_name}({hook.args_with_type})
            """)
            list_with_hook_specs_with_documentation += hook_specs_content

        file_content = dedent(f"""\
        /* {self._DO_NOT_MODIFY_MSG} */
        #ifndef {self.project_name.upper()}_HOOK_SPECS_HEADER_FILE
        #define {self.project_name.upper()}_HOOK_SPECS_HEADER_FILE
        #ifdef __cplusplus
            #define _HOOKMAN_EXTERN_C extern "C"
        #else
            #define _HOOKMAN_EXTERN_C
        #endif

        #ifdef WIN32
            #define HOOKMAN_API_EXP _HOOKMAN_EXTERN_C __declspec(dllexport)
            #define HOOKMAN_FUNC_EXP __cdecl
        #else
            #define HOOKMAN_API_EXP _HOOKMAN_EXTERN_C
            #define HOOKMAN_FUNC_EXP
        #endif

        HOOKMAN_API_EXP const char* HOOKMAN_FUNC_EXP {self.project_name}_version_api() {{
            return \"{self.version}\";
        }}

        HOOKMAN_API_EXP const char* HOOKMAN_FUNC_EXP get_plugin_name() {{
            return \"{shared_lib_name}\";
        }}

        """)
        file_content += list_with_hook_specs_with_documentation
        file_content += dedent(f"""
        
        #endif // {self.project_name.upper()}_HOOK_SPECS_HEADER_FILE
        """)
        return file_content

    _DO_NOT_MODIFY_MSG = 'File automatically generated by hookman, **DO NOT MODIFY MANUALLY**'

    def _hook_caller_hpp_content(self) -> str:
        """
        Create a .hpp file with the content informed on the hook_specs
        """
        content_lines = []
        list_with_hook_calls = []
        list_with_set_functions = []
        list_with_private_members = []

        content_lines += [
            f"// {self._DO_NOT_MODIFY_MSG}",
            "#ifndef _H_HOOKMAN_HOOK_CALLER",
            "#define _H_HOOKMAN_HOOK_CALLER",
            "",
            "#include <functional>",
            "#include <stdexcept>",
            "#include <string>",
            "#include <vector>",
            "",
            "#ifdef _WIN32",
            f"    #include <windows.h>",
            "#else",
            f"    #include <dlfcn.h>",
            "#endif",
            "",
        ]
        content_lines += (f'#include <{x}>' for x in self.extra_includes)
        content_lines += [
            "",
            "namespace hookman {",
            "",
            "template <typename F_TYPE> std::function<F_TYPE> from_c_pointer(uintptr_t p) {",
            f"    return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));",
            "}",
            "",
            "class HookCaller {",
            "public:",
        ]

        for hook in self.hooks:
            list_with_hook_calls += [
                f'    std::vector<std::function<{hook.r_type}({hook.args_type})>> {hook.name}_impls() {{',
                f'        return this->_{hook.name}_impls;',
                f'    }}',
            ]
            list_with_private_members += [
                f'    std::vector<std::function<{hook.r_type}({hook.args_type})>> _{hook.name}_impls;'
            ]

            list_with_set_functions += [
                # uintptr overload
                f'    void append_{hook.name}_impl(uintptr_t pointer) {{',
                f'        this->_{hook.name}_impls.push_back(from_c_pointer<{hook.r_type}({hook.args_type})>(pointer));',
                f'    }}',
                "",
                # std::function overload
                f'    void append_{hook.name}_impl(std::function<{hook.r_type}({hook.args_type})> func) {{',
                f'        this->_{hook.name}_impls.push_back(func);',
                f'    }}',
            ]
        content_lines += list_with_hook_calls
        content_lines.append("")
        content_lines += list_with_set_functions
        content_lines.append("")
        content_lines += _generate_load_function(self.hooks)
        content_lines.append("private:")
        content_lines += list_with_private_members
        content_lines.append("};")
        content_lines.append("")
        content_lines.append("}  // namespace hookman")
        content_lines.append("#endif // _H_HOOKMAN_HOOK_CALLER")
        content_lines.append('')

        return "\n".join(content_lines)

    def _hook_caller_python_content(self) -> str:
        """
        Create a .cpp file to bind python and cpp code with PyBind11
        """
        content_lines = [
            f"// {self._DO_NOT_MODIFY_MSG}",
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
            content_lines.append(f'    py::bind_vector<{vector_type}>(m, "{name}", "Hook for vector implementation type {index}");')
        content_lines.append("")

        content_lines += [
            f'    py::class_<hookman::HookCaller>(m, "HookCaller")',
            f"        .def(py::init<>())",
            f'        .def("load_impls_from_library", &hookman::HookCaller::load_impls_from_library)',
        ]
        for hook in self.hooks:
            append_ptr = f'&hookman::HookCaller::append_{hook.name}_impl'
            append_uint_sig = 'void (hookman::HookCaller::*)(uintptr_t)'
            append_function_sig = f'void (hookman::HookCaller::*)(std::function<{hook.r_type}({hook.args_type})>)'

            content_lines += [
                f'        .def("{hook.name}_impls", &hookman::HookCaller::{hook.name}_impls)',
                f'        .def("append_{hook.name}_impl", ({append_uint_sig}) {append_ptr})',
                f'        .def("append_{hook.name}_impl", ({append_function_sig}) {append_ptr})',
            ]
        content_lines.append(f'    ;')
        content_lines.append('}')
        content_lines.append('')
        return "\n".join(content_lines)

    def _generate_cmake_files(self, dst_path: Path):
        from textwrap import dedent

        hook_caller_hpp = Path(dst_path / 'cpp' / 'CMakeLists.txt')
        with open(hook_caller_hpp, mode='w') as file:
            file.writelines(dedent(f"""\
                add_library({self.pyd_name}_interface INTERFACE)
                target_include_directories({self.pyd_name}_interface INTERFACE ./)
                """))

        if self.pyd_name:
            hook_caller_python = Path(dst_path / 'binding' / 'CMakeLists.txt')
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
        plugin_hooks_macro = [f'// HOOK_{hook.macro_name}({hook.args}){{}}\n' for hook in self.hooks]

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


def _generate_load_function(hooks):
    result = [
        "#if defined(_WIN32)",
        "",
    ]
    result += _generate_windows_body(hooks)
    result += [
        "",
        "#elif defined(__linux__)",
        "",
    ]
    result += _generate_linux_body(hooks)
    result += [
        "",
        "#else",
        f'    #error "unknown platform"',
        "#endif",
        "",
    ]
    return result


def _generate_windows_body(hooks):
    """Generate Windows specific functions.

    At the moment it implements load_impls_from_library, class destructor, and an utility function
    to convert from utf8 to wide-strings so we can use the wide family of windows
    functions that accept unicode.
    """
    # generate destructor to free the library handles opened by load_from_library()
    result = [
        "public:",
        f"    ~HookCaller() {{",
        f"        for (auto handle : this->handles) {{",
        f"            FreeLibrary(handle);",
        f"        }}",
        f"    }}",
    ]

    # generate load_impls_from_library()
    result += [
        f"    void load_impls_from_library(const std::string& utf8_filename) {{",
        f'        std::wstring w_filename = utf8_to_wstring(utf8_filename);',
        f'        auto handle = LoadLibraryW(w_filename.c_str());',
        f'        if (handle == NULL) {{',
        f'            throw std::runtime_error("Error loading library " + utf8_filename + ": " + std::to_string(GetLastError()));',
        f'        }}',
        f'        this->handles.push_back(handle);',
        "",
    ]

    for index, hook in enumerate(hooks):
        result += [
            f'        auto p{index} = GetProcAddress(handle, "{hook.function_name}");',
            f'        if (p{index} != nullptr) {{',
            f'            this->append_{hook.name}_impl((uintptr_t)(p{index}));',
            f'        }}',
            "",
        ]
    result.append("    }")

    result += [
        "",
        "",
        "private:",
        f"    std::wstring utf8_to_wstring(const std::string& s) {{",
        f"        int flags = 0;",
        f"        int required_size = MultiByteToWideChar(CP_UTF8, flags, s.c_str(), -1, nullptr, 0);",
        f"        std::wstring result;",
        f"        if (required_size == 0) {{",
        f"            return result;",
        f"        }}",
        f"        result.resize(required_size);",
        f"        int err = MultiByteToWideChar(CP_UTF8, flags, s.c_str(), -1, &result[0], required_size);",
        f"        if (err == 0) {{",
        f"            // error handling: https://docs.microsoft.com/en-us/windows/desktop/api/stringapiset/nf-stringapiset-multibytetowidechar#return-value",
        f"            switch (GetLastError()) {{",
        f"                case ERROR_INSUFFICIENT_BUFFER: throw std::runtime_error(\"utf8_to_wstring: ERROR_INSUFFICIENT_BUFFER\");",
        f"                case ERROR_INVALID_FLAGS: throw std::runtime_error(\"utf8_to_wstring: ERROR_INVALID_FLAGS\");",
        f"                case ERROR_INVALID_PARAMETER: throw std::runtime_error(\"utf8_to_wstring: ERROR_INVALID_PARAMETER\");",
        f"                case ERROR_NO_UNICODE_TRANSLATION: throw std::runtime_error(\"utf8_to_wstring: ERROR_NO_UNICODE_TRANSLATION\");",
        f"                default: throw std::runtime_error(\"Undefined error: \" + std::to_string(GetLastError()));",
        f"            }}",
        f"        }}",
        f"        return result;",
        f"    }}",
        f"",
        f"",
        f"private:",
        f"    std::vector<HMODULE> handles;",
    ]
    return result


def _generate_linux_body(hooks):
    """
    Generate linux specific functions.

    At the moment it implements load_impls_from_library and the class destructor
    to cleanup handles.
    """
    # generate destructor to free the library handles opened by load_from_library()
    result = [
        f"private:",
        f"    std::vector<void*> handles;",
        "",
        "public:",
        f"    ~HookCaller() {{",
        f"        for (auto handle : this->handles) {{",
        f"            dlclose(handle);",
        f"        }}",
        f"    }}",
    ]

    # generate load_impls_from_library()
    result += [
        f"    void load_impls_from_library(const std::string& utf8_filename) {{",
        f'        auto handle = dlopen(utf8_filename.c_str(), RTLD_LAZY);',
        f'        if (handle == nullptr) {{',
        f'            throw std::runtime_error("Error loading library " + utf8_filename + ": dlopen failed");',
        f'        }}',
        f'        this->handles.push_back(handle);',
        "",
    ]

    for index, hook in enumerate(hooks):
        result += [
            f'        auto p{index} = dlsym(handle, "{hook.function_name}");',
            f'        if (p{index} != nullptr) {{',
            f'            this->append_{hook.name}_impl((uintptr_t)(p{index}));',
            f'        }}',
            "",
        ]
    result.append("    }")
    return result
