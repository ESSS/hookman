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


class HookManGenerator():
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
            raise FileNotFoundError("File not found: {}".format(hook_spec_file_path))

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

    def generate_files(self, dst_path: Path):
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

        with open(hook_specs_h, mode='w') as file:
            file.writelines(hook_specs_h_content)

        with open(hook_caller_hpp, mode='w') as file:
            file.writelines(hook_caller_hpp_content)

        with open(hook_caller_python, mode='w') as file:
            file.writelines(hook_caller_python_content)

        self._generate_cmake_files(dst_path)

    def _hook_specs_header_content(self) -> List[str]:
        """
        Create a C header file with the content informed on the hook_specs
        """
        file_content = []
        list_with_hook_specs_arguments = []

        for hook in self.hooks:
            line = f'#define HOOK_{hook.macro_name}({hook.args}) API_EXP {hook.r_type} FUNC_EXP {hook.function_name}({hook.args_with_type})' + NEW_LINE
            list_with_hook_specs_arguments.append(line)

        from textwrap import dedent
        file_content += dedent(f"""\
        #ifndef HEADER_FILE
        #define HEADER_FILE
        #ifdef WIN32
            #define API_EXP __declspec(dllexport)
            #define FUNC_EXP __cdecl
        #else
            #define API_EXP
            #define FUNC_EXP
        #endif

        #define INIT_HOOKS() API_EXP char* FUNC_EXP {self.project_name}_version_api() {{return \"{self.version}\";}}
        """)
        file_content += list_with_hook_specs_arguments
        file_content += dedent(f"""
        #endif
        """)
        return file_content

    def _hook_caller_hpp_content(self) -> List[str]:
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

        namespace HookMan {{

        template <typename F_TYPE> std::function<F_TYPE> register_c_func(uintptr_t p) {{
        {INDENTATION}return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));
        }}

        class HookCaller {{
        public:
        """)

        list_with_hook_calls += [
            f'{INDENTATION}inline {hook.r_type} {hook.name}({hook.args_with_type}) {{ return this->_{hook.name}({hook.args}); }}' + NEW_LINE
            for hook in self.hooks
        ]

        list_with_private_members += [
            f'{INDENTATION}std::function<{hook.r_type}({hook.args_type})> _{hook.name};' + NEW_LINE
            for hook in self.hooks
        ]

        list_with_set_functions += [
            f'{1*INDENTATION}void set_{hook.name}_function(uintptr_t pointer) {{' + NEW_LINE +
            f'{2*INDENTATION}this->_{hook.name} = register_c_func<{hook.r_type}({hook.args_type})>(pointer);' + NEW_LINE +
            f'{1*INDENTATION}}}' + 2 * NEW_LINE
            for hook in self.hooks
        ]
        file_content += list_with_hook_calls
        file_content += NEW_LINE
        file_content += list_with_set_functions
        file_content += "private:" + NEW_LINE
        file_content += list_with_private_members
        file_content += "};" + NEW_LINE + "}" + NEW_LINE

        return file_content

    def _hook_caller_python_content(self) -> List[str]:
        """
        Create a .cpp file to bind python and cpp code with PyBind11
        """
        file_content = []
        file_content += dedent(f"""\
            #include <pybind11/pybind11.h>
            #include <HookCaller.hpp>

            namespace py = pybind11;

            PYBIND11_MODULE({self.pyd_name}, m) {{
                py::class_<HookMan::HookCaller>(m, "HookCaller")
                    .def(py::init<>())
        """)
        file_content += [
            f'{2*INDENTATION}.def("set_{hook.name}_function", &HookMan::HookCaller::set_{hook.name}_function)' + NEW_LINE
            for hook in self.hooks
        ]
        file_content += f'{2*INDENTATION};' + NEW_LINE + '}' + NEW_LINE
        return file_content

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
            include(pybind11Tools)
            
            pybind11_add_module(
                {self.pyd_name}
                    HookCallerPython.cpp
            )
            
            target_link_libraries(
                {self.pyd_name}
                PRIVATE
                    {self.pyd_name}_interface
            )
            
            install(TARGETS {self.pyd_name} EXPORT ${{PROJECT_NAME}}_export DESTINATION ${{LIBS_DIR}})
            """))
