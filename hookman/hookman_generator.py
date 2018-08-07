import importlib
import inspect
import os
from pathlib import Path
from textwrap import dedent
from typing import List, NamedTuple

from hookman.hooks import HooksSpecs

INDENTATION = "    "
NEW_LINE = "\n"


class Hook(NamedTuple):
    """
    Class to assist on the process to generate the files

    name: Name of the Hook
    macro_name: Name of the Hook in Upper Case
    r_type: Type of the return from the hook

    args: The name of each argument
        Ex.: v1, v2, v3
    args_type: The type of each argument
        Ex.: int, float, int
    args_with_type: The name of the argument with the type
        Ex.: int v1, float v2, int v3

    function_name: Full name of the hook function
        Ex.: project_name_version_hook_name -> alfasim_v4_friction_factory
    """
    name: str
    macro_name: str
    r_type: str
    args: str
    args_type: str
    args_with_type: str
    function_name: str


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

    def _import_hook_specification_file(self, hook_spec_file_path: Path) -> HooksSpecs:
        """
        Returns the "HooksSpecs" object that defines the hook specification provide from the project.
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

    def _populate_local_variables(self, hook_specs: HooksSpecs):
        """
        Populate the self.hooks property with the given hook specification.
        See the docstring from the Hook type for more details about the self.hooks
        """
        self.project_name = hook_specs.project_name.lower()
        self.pyd_name = hook_specs.pyd_name
        self.version = f'v{hook_specs.version}'

        def format_arguments(text_list: List[str]) -> str:
            """
            Format the REPR from the args list ("['v1', 'v2']") to an acceptable format ("v1, v2")
            """
            text = str(text_list)
            return text.replace('[', '').replace(']', '').replace('\'', '')

        self.hooks = []
        for hook_spec in hook_specs.hooks:
            hook_arg_spec = inspect.getfullargspec(hook_spec)
            hook_arguments = hook_arg_spec.args
            hook_types = hook_arg_spec.annotations
            self.hooks.append(
                Hook(
                    name=hook_spec.__name__.lower(),
                    macro_name=hook_spec.__name__.upper(),
                    r_type=hook_arg_spec.annotations['return'],
                    args=format_arguments(hook_arguments),
                    args_type=format_arguments([f"{hook_types[arg]}" for arg in hook_arguments]),
                    args_with_type=format_arguments(
                        [f"{hook_types[arg]} {arg}" for arg in hook_arguments]),
                    function_name=f'{self.project_name}_{self.version}_{hook_spec.__name__.lower()}',
                ))

    def generate_plugin_template(self,
            plugin_name: str ,
            shared_lib_name: str,
            author_email: str,
            author_name:str ,
            dst_path: Path):
        """
        Generate a template with the necessary files and structure to create a plugin
            - config.yml
            - plugin.c
            - hook_specs.h
            - CMakeLists file
            - README
        """
        plugin_folder = dst_path / plugin_name
        if not plugin_folder.exists():
            plugin_folder.mkdir(parents=True)

        plugin_readme_file = Path(plugin_folder / 'README.md')
        plugin_config_file = Path(plugin_folder / 'config.yaml')
        plugin_source_code_file = Path(plugin_folder / 'plugin.c')
        hook_specs_header_file = Path(plugin_folder / 'hook_specs.h')
        plugin_cmake_file = Path(plugin_folder / 'CMakeLists.txt')
        build_script_file = Path(plugin_folder / 'build.py')

        plugin_readme_content = self._readme_content(plugin_name, author_email, author_name)
        plugin_config_content = self._plugin_config_file_content(plugin_name, shared_lib_name, author_email, author_name,)
        plugin_source_code_content = self._plugin_source_content()
        hook_specs_header_content = self._hook_specs_header_content()
        plugin_cmake_content = self._plugin_cmake_file_content(shared_lib_name)
        build_script_content = self._build_shared_lib_python_script_content(shared_lib_name)

        plugin_readme_file.write_text(plugin_readme_content)
        plugin_config_file.write_text(plugin_config_content)
        plugin_source_code_file.write_text(plugin_source_code_content)
        hook_specs_header_file.write_text(hook_specs_header_content)
        plugin_cmake_file.write_text(plugin_cmake_content)
        build_script_file.write_text(build_script_content)

    def generate_project_files(self, dst_path: Path):
        """
        Generate the following files on the dst_path:
            - hook_specs.h
            - HookCaller.hpp
            - HookCallerPython.cpp
        """
        hook_specs_h = Path(dst_path / 'plugin' / 'hook_specs.h')
        hook_caller_hpp = Path(dst_path / 'cpp' / 'HookCaller.hpp')
        hook_caller_python = Path(dst_path / 'binding' / 'HookCallerPython.cpp')

        os.makedirs(hook_specs_h.parent)
        os.makedirs(hook_caller_hpp.parent)
        os.makedirs(hook_caller_python.parent)

        hook_specs_h_content = self._hook_specs_header_content()
        hook_caller_hpp_content = self._hook_caller_hpp_content()
        hook_caller_python_content = self._hook_caller_python_content()

        hook_specs_h.write_text(hook_specs_h_content)
        hook_caller_hpp.write_text(hook_caller_hpp_content)
        hook_caller_python.write_text(hook_caller_python_content)

        self._generate_cmake_files(dst_path)

    def _hook_specs_header_content(self) -> str:
        """
        Create a C header file with the content informed on the hook_specs
        """
        file_content = []
        list_with_hook_specs_arguments = []

        for hook in self.hooks:
            line = f'#define HOOK_{hook.macro_name}({hook.args}) HOOKMAN_API_EXP {hook.r_type} HOOKMAN_FUNC_EXP {hook.function_name}({hook.args_with_type})' + NEW_LINE
            list_with_hook_specs_arguments.append(line)

        from textwrap import dedent
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

        #define INIT_HOOKS() HOOKMAN_API_EXP char* HOOKMAN_FUNC_EXP {self.project_name}_version_api() {{return \"{self.version}\";}}
        """)
        file_content += list_with_hook_specs_arguments
        file_content += dedent(f"""
        #endif
        """)
        return ''.join(file_content)

    def _hook_caller_hpp_content(self) -> str:
        """
        Create a .hpp file with the content informed on the hook_specs
        """
        file_content = []
        list_with_hook_calls = []
        list_with_set_functions = []
        list_with_private_members = []
        from textwrap import dedent

        file_content += dedent(f"""\
        #include <functional>

        namespace hookman {{

        template <typename F_TYPE> std::function<F_TYPE> from_c_pointer(uintptr_t p) {{
        {INDENTATION}return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));
        }}

        class HookCaller {{
        public:
        """)

        list_with_hook_calls += [
            f'{INDENTATION}std::function<{hook.r_type}({hook.args_type})> {hook.name}() {{' + NEW_LINE +
            f'{INDENTATION*2}return this->_{hook.name};' + NEW_LINE +
            f'{INDENTATION}}}' + NEW_LINE
            for hook in self.hooks
        ]
        list_with_private_members += [
            f'{INDENTATION}std::function<{hook.r_type}({hook.args_type})> _{hook.name};' + NEW_LINE
            for hook in self.hooks
        ]

        list_with_set_functions += [
            f'{1*INDENTATION}void set_{hook.name}_function(uintptr_t pointer) {{' + NEW_LINE +
            f'{2*INDENTATION}this->_{hook.name} = from_c_pointer<{hook.r_type}({hook.args_type})>(pointer);' + NEW_LINE +
            f'{1*INDENTATION}}}' + 2 * NEW_LINE
            for hook in self.hooks
        ]
        file_content += list_with_hook_calls
        file_content += NEW_LINE
        file_content += list_with_set_functions
        file_content += "private:" + NEW_LINE
        file_content += list_with_private_members
        file_content += "};" + NEW_LINE + "}" + NEW_LINE

        return ''.join(file_content)

    def _hook_caller_python_content(self) -> str:
        """
        Create a .cpp file to bind python and cpp code with PyBind11
        """
        file_content = []
        file_content += dedent(f"""\
            #include <pybind11/pybind11.h>
            #include <pybind11/functional.h>
            #include <HookCaller.hpp>

            namespace py = pybind11;

            PYBIND11_MODULE({self.pyd_name}, m) {{
                py::class_<hookman::HookCaller>(m, "HookCaller")
                    .def(py::init<>())
        """)
        file_content += [
            f'{2*INDENTATION}.def("{hook.name}", &hookman::HookCaller::{hook.name})' + NEW_LINE +
            f'{2*INDENTATION}.def("set_{hook.name}_function", &hookman::HookCaller::set_{hook.name}_function)' + NEW_LINE
            for hook in self.hooks
        ]
        file_content += f'{2*INDENTATION};' + NEW_LINE + '}' + NEW_LINE
        return ''.join(file_content)

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

            install(TARGETS {self.pyd_name} EXPORT ${{PROJECT_NAME}}_export DESTINATION ${{LIBS_DIR}})
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

         Here's an overview of the syntax that you can use to write the content of this file:

         Headers
            # This is equivalent an <h1> tag on html
            ## This equivalent an <h2> tag on html

         Emphasis
            *This text will be italic*
            _This will also be italic_

            **This text will be bold**
            __This will also be bold__

        Lists
            Unordered
                * Item 1
                * Item 2
                    * Item 2a
                    * Item 2b
            Ordered
                1. Item 1
                2. Item 2
                3. Item 3
                   3.1. Item 3a
                   3.2. Item 3b

        Images
            Format: ![Alt Text](url)

        Links
            http://github.com - automatic!
            [Display Name](http://<link>)

        Blockquotes
            > Blockquote
            >> Nested blockquote

        Inline code
            ` some code `

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
            project ({shared_lib_name} LANGUAGES CXX C)

            if(NOT WIN32)
              set(CMAKE_C_COMPILER    clang)
              set(CMAKE_CXX_COMPILER  clang++)
              set(CMAKE_C_FLAGS       "-Wall -std=c99")
              set(CMAKE_C_FLAGS_DEBUG "-g")
            endif(NOT WIN32)

            set(CMAKE_CXX_FLAGS       "-Wall -Werror=return-type -ftemplate-depth=1024")
            set(CMAKE_CXX_LINK_FLAGS  "-lstdc++")
            set(CMAKE_CXX_FLAGS_DEBUG "-g")


            set(CMAKE_C_STANDARD 99)

            add_library({shared_lib_name} SHARED plugin.c hook_specs.h)
            install(TARGETS acme EXPORT ${{PROJECT_NAME}}_export DESTINATION ${{CMAKE_CURRENT_SOURCE_DIR}})
        ''')
        return file_content

    def _build_shared_lib_python_script_content(self, shared_lib_name):
        file_content = dedent(f'''\
            import os
            import shutil
            import subprocess
            from pathlib import Path

            current_dir = Path(os.getcwd())
            build_dir = current_dir / "build"
            shared_lib = build_dir / "Release/{shared_lib_name}.dll"

            if build_dir.exists():
                shutil.rmtree(build_dir)

            build_dir.mkdir()

            binary_directory_path = f"-B{{str(build_dir)}}"
            home_directory_path = f"-H{{current_dir}}"

            subprocess.run(["cmake", binary_directory_path, home_directory_path])
            subprocess.run(["cmake", "--build", str(build_dir), "--config", "Release"])
            subprocess.run(["cp", str(shared_lib), str(current_dir)])
        ''')
        return file_content
