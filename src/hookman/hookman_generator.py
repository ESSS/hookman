import importlib.util
import inspect
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from textwrap import dedent
from typing import Any
from typing import NamedTuple
from zipfile import ZipFile

from hookman.exceptions import ArtifactsDirNotFoundError
from hookman.exceptions import AssetsDirNotFoundError
from hookman.exceptions import HookmanError
from hookman.hooks import HookSpecs
from hookman.plugin_config import PLUGIN_CONFIG_SCHEMA
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

    def __init__(self, hook_spec_file_path: Path | str) -> None:
        """
        Receives a path to a hooks specification file.
        if the Path provided is not a file an exception FileNotFoundError is raised.
        If the File provided doesn't have a spec object, a RuntimeError is raised.
        """
        hook_spec_file_path = Path(hook_spec_file_path)
        if hook_spec_file_path.is_file():
            specs = self._import_hook_specs_from_module(hook_spec_file_path)
            self._populate_local_variables(specs)
        else:
            raise FileNotFoundError(f"File not found: {hook_spec_file_path}")

    def _import_hook_specs_from_module(self, hook_spec_file_path: Path) -> HookSpecs:
        """
        Returns the "HookSpecs" object that defines the hook specification provide from the project.
        The file is considered valid if the importlib can access the object called "specs"

        :param hook_spec_file_path: Path to the location of the file
        :return: A Python module that represent specification from the given file
        """
        spec = importlib.util.spec_from_file_location("hook_specs", hook_spec_file_path)
        assert spec is not None, f"Could not find spec for {hook_spec_file_path}"
        assert spec.loader is not None, f"Loader cannot be None for {hook_spec_file_path}"
        module = importlib.util.module_from_spec(spec)
        assert module is not None, f"Could not find module for {hook_spec_file_path}"
        spec.loader.exec_module(module)
        try:
            specs = getattr(module, "specs")
        except AttributeError:
            raise RuntimeError(f"Invalid module {module}, 'specs' variable not defined.")
        else:
            if not isinstance(specs, HookSpecs):
                raise RuntimeError(
                    f"{module}.specs is {specs!r}, expected type '{HookSpecs.__name__}'"
                )
            return specs

    def _populate_local_variables(self, hook_specs: HookSpecs) -> None:
        """
        Populate the self.hooks property with the given hook specification.
        See the docstring from the Hook type for more details about the self.hooks
        """
        self.project_name = hook_specs.project_name.lower()
        self.pyd_name = hook_specs.pyd_name
        self.version = f"v{hook_specs.version}"

        def get_arg_with_type(arg: str) -> str:
            arg_type = hook_types[arg]
            array_type_pattern = (
                r"(?P<array_type>.+)"  # `double ` in `double [ 2 ]`
                r"(?:\s*\[\s*"  # `[` and possible spaces
                r"(?P<array_size>\d*)"  # `2` in `double [ 2 ]` or empty in `int[]`
                r"\s*\]\s*)$"  # `]` with possible spaces and end of string
            )
            m = re.match(array_type_pattern, arg_type)
            if m is not None:
                array_type = m.group("array_type").strip()
                array_size = m.group("array_size")
                return f"{array_type} {arg}[{array_size}]"
            return f"{arg_type.strip()} {arg}"

        self.extra_includes = hook_specs.extra_includes
        self.hooks = []
        for hook_spec in hook_specs.hooks:
            hook_documentation = inspect.getdoc(hook_spec) or ""
            hook_arg_spec = inspect.getfullargspec(hook_spec)
            hook_arguments = hook_arg_spec.args
            hook_types = hook_arg_spec.annotations
            self.hooks.append(
                Hook(
                    args=", ".join(hook_arguments),
                    args_type=", ".join([f"{hook_types[arg]}" for arg in hook_arguments]),
                    args_with_type=", ".join(get_arg_with_type(arg) for arg in hook_arguments),
                    documentation=hook_documentation,
                    function_name=f"{self.project_name}_{self.version}_{hook_spec.__name__.lower()}",
                    macro_name=hook_spec.__name__.upper(),
                    name=hook_spec.__name__.lower(),
                    r_type=hook_arg_spec.annotations["return"],
                )
            )

    def generate_plugin_template(
        self,
        caption: str,
        plugin_id: str,
        author_email: str,
        author_name: str,
        dst_path: Path,
        extra_includes: list[str] | None = None,
        extra_body_lines: list[str] | None = None,
        exclude_hooks: list[str] | None = None,
        extras: Mapping[str, str] | None = None,
        requirements: Mapping[str, str] | None = None,
    ) -> None:
        """
        Generate a template with the necessary files and structure to create a plugin

        :param str caption: the user-friendly name of the plugin, for example ``"Hydrates"``.

        A folder with the same name as the plugin_id argument will be created, with the following files:
            <plugin_folder>
                - CMakeLists.txt
                - compile.py
                assets/
                    - plugin.yaml
                    - README.md
                    - CHANGELOG.rst
                src/
                    - hook_specs.h
                    - {plugin_id}.cpp
                    - CMakeLists.txt

        :param extra_includes:
            Extras include to be added on {plugin_id}.cpp as "default", as an example is the includes for a SDK.

        :param requirements:
            The requirements needed to create the plugin template.

        :param extra_body_lines:
            Extras lines to be added on {plugin_id}.cpp on the body, used for default implementations of hooks

        :param exclude_hooks:
            List of hooks, that will not be inserted on the {plugin_id}.cpp
        """
        if not plugin_id.isidentifier():
            raise HookmanError("The shared library name must be a valid identifier.")

        plugin_folder = dst_path / plugin_id
        assets_folder = plugin_folder / "assets"
        source_folder = plugin_folder / "src"

        if not plugin_folder.exists():
            plugin_folder.mkdir(parents=True)

        if not assets_folder.exists():
            assets_folder.mkdir()

        if not source_folder.exists():
            source_folder.mkdir()

        extra_includes = self._validate_parameter("extra_includes", extra_includes)
        extra_body_lines = self._validate_parameter("extra_body_lines", extra_body_lines)
        exclude_hooks = self._validate_parameter("exclude_hooks", exclude_hooks)

        Path(plugin_folder / "compile.py").write_text(
            self._compile_shared_lib_python_script_content(plugin_id)
        )
        Path(plugin_folder / "CMakeLists.txt").write_text(
            self._plugin_cmake_file_content(plugin_id)
        )
        Path(assets_folder / "plugin.yaml").write_text(
            self._plugin_config_file_content(
                caption, plugin_id, author_email, author_name, extras, requirements
            )
        )
        Path(assets_folder / "README.md").write_text(
            self._readme_content(caption, author_email, author_name)
        )
        Path(assets_folder / "CHANGELOG.rst").write_text(self._changelog_content(caption))
        Path(source_folder / "hook_specs.h").write_text(self._hook_specs_header_content(plugin_id))
        Path(source_folder / f"{plugin_id}.cpp").write_text(
            self._plugin_source_content(extra_includes, extra_body_lines, exclude_hooks)
        )
        Path(source_folder / "CMakeLists.txt").write_text(
            self._plugin_src_cmake_file_content(plugin_id)
        )

    def _validate_parameter(self, parameter_name: str, parameter_value: Any) -> list[str]:
        """
        Check if the given parameter is a list and if all elements of this list are strings
        """

        if parameter_value is None:
            parameter_value = []

        if not isinstance(parameter_value, list):
            raise ValueError(
                f"{parameter_name} parameter must be a list, got {type(parameter_value).__name__}"
            )

        # Check if the list is empty otherwise check if all elements of the list are strings
        if parameter_value and not all(isinstance(i, str) for i in parameter_value):
            raise ValueError(f"All elements of {parameter_name} must be a string")

        return parameter_value

    def generate_hook_specs_header(self, plugin_id: str, dst_path: str | Path) -> None:
        """Generates the "hook_specs.h" file which is consumed by plugins to implement the hooks.

        :param plugin_id: short name of the generated shared library
        :param dst_path: directory where to generate the file.
        """
        source_folder = Path(dst_path) / plugin_id / "src"
        source_folder.mkdir(parents=True, exist_ok=True)
        Path(source_folder / "hook_specs.h").write_text(self._hook_specs_header_content(plugin_id))

    def generate_project_files(self, dst_path: Path | str) -> None:
        """
        Generate the following files on the dst_path:
        - HookCaller.hpp
        - HookCallerPython.cpp
        """
        dst_path = Path(dst_path)
        hook_caller_hpp = dst_path / "cpp/HookCaller.hpp"
        hook_caller_hpp.parent.mkdir(exist_ok=True, parents=True)
        hook_caller_hpp.write_text(self._hook_caller_hpp_content())

        if self.pyd_name:
            hook_caller_python = dst_path / "binding/HookCallerPython.cpp"
            hook_caller_python.parent.mkdir(exist_ok=True, parents=True)
            hook_caller_python.write_text(self._hook_caller_python_content())

        self._generate_cmake_files(dst_path)

    def generate_plugin_package(
        self,
        package_name: str,
        plugin_dir: Path | str,
        dst_path: Path | None = None,
        extras_defaults: Mapping[str, str] | None = None,
        requirements: Mapping[str, str] | None = None,
        package_name_suffix: str | None = None,
    ) -> None:
        """
        Creates a .hmplugin file using the name provided on package_name argument.
        The file `.hmplugin` will be created with the content from the folder assets and artifacts.

        In order to successfully creates a plugin, at least the following files should be present:
            - plugin.yml
            - shared library (.ddl or .so)
            - readme.md
            - changelog.rst

        Per default, the package will be created inside the folder plugin_dir, however it's possible
        to give another path filling the dst argument

        :param Dict[str,str] extras_defaults:
            (key, value) entries to be added to "extras" if not defined by the original input yaml.

        :param requirements:
            The requirements necessary to generate the plugin.

        :param Optional[str] package_name_suffix:
            If not `None` this string is inserted after the plugin version in the filename.
        """
        import strictyaml

        plugin_dir = Path(plugin_dir)
        if dst_path is None:
            dst_path = plugin_dir

        assets_dir = plugin_dir / "assets"
        artifacts_dir = plugin_dir / "artifacts"
        python_dir = plugin_dir / "src" / "python"

        self._validate_package_folder(artifacts_dir, assets_dir)
        self._validate_plugin_config_file(assets_dir / "plugin.yaml")
        plugin_info = PluginInfo(assets_dir / "plugin.yaml", hooks_available=None)

        contents = (assets_dir / "plugin.yaml").read_text()
        if extras_defaults is not None:
            contents_dict = strictyaml.load(contents, PLUGIN_CONFIG_SCHEMA)
            extras = dict(extras_defaults)
            extras.update(contents_dict.data.get("extras", {}))
            contents_dict["extras"] = dict(sorted(extras.items()))
            contents = contents_dict.as_yaml()

        if requirements is not None:
            contents_dict = strictyaml.load(contents, PLUGIN_CONFIG_SCHEMA)
            contents_dict["requirements"] = dict(sorted(requirements.items()))
            contents = contents_dict.as_yaml()

        hmplugin_base_name_components = [package_name, plugin_info.version.base_version]
        if package_name_suffix is not None:
            hmplugin_base_name_components.append(package_name_suffix)

        if sys.platform == "win32":  # pragma: no cover (apparently merge reports of the same files)
            shared_lib_extension = "*.dll"
            hmplugin_base_name_components.append("win64")
            shared_lib_files = artifacts_dir.rglob(shared_lib_extension)
        else:
            shared_lib_extension = "*.so"
            shared_lib_versioned_extension = "*.so.[0-9]*"
            shared_lib_files = list(artifacts_dir.rglob(shared_lib_extension)) + list(
                artifacts_dir.rglob(shared_lib_versioned_extension)
            )
            hmplugin_base_name_components.append("linux64")

        hmplugin_path = dst_path / ("-".join(hmplugin_base_name_components) + ".hmplugin")
        with ZipFile(hmplugin_path, "w") as zip_file:
            for file in assets_dir.rglob("*"):
                if file.name == "plugin.yaml":
                    zip_file.writestr(str(file.relative_to(plugin_dir)), data=contents)
                else:
                    zip_file.write(filename=file, arcname=file.relative_to(plugin_dir))

            for file in shared_lib_files:
                zip_file.write(filename=file, arcname=file.relative_to(plugin_dir))

            for file in python_dir.rglob("*"):
                dst_filename = Path("artifacts" / file.relative_to(plugin_dir / "src/python"))
                zip_file.write(filename=file, arcname=dst_filename)

    def _validate_package_folder(self, artifacts_dir: Path, assets_dir: Path) -> None:
        """
        Method to ensure that the plugin folder has the following criteria:
            - An "assets" folder should be present
            - An "artifacts" folder should be present

            - The assets folder needs to contain:
                - Readme.md
                - changelog.rst
                - plugin.yaml

            - The artifacts folder need to contain:
                - At least one shared library (.dll or .so)

            - The plugin.yaml should have the name of the main library in the "plugin_id" entry.
        """
        if not assets_dir.exists():
            raise AssetsDirNotFoundError()

        if not artifacts_dir.exists():
            raise ArtifactsDirNotFoundError(f"Artifacts directory not found: {artifacts_dir}")

        shared_lib_extension = "*.dll" if sys.platform == "win32" else "*.so"
        if not any(artifacts_dir.rglob(shared_lib_extension)):
            raise FileNotFoundError(
                f"Unable to locate a shared library ({shared_lib_extension}) in {artifacts_dir}"
            )

        if not assets_dir.joinpath("plugin.yaml").is_file():
            raise FileNotFoundError(f"Unable to locate the file plugin.yaml in {assets_dir}")

        if not assets_dir.joinpath("README.md").is_file():
            raise FileNotFoundError(f"Unable to locate the file README.md in {assets_dir}")

        if not assets_dir.joinpath("CHANGELOG.rst").is_file():
            raise FileNotFoundError(f"Unable to locate the file CHANGELOG.rst in {assets_dir}")

    def _validate_plugin_config_file(self, plugin_config_file: Path) -> None:
        """
        Check if the given plugin_file is valid, by creating a instance of PluginInfo.
        All checks are made in the __init__
        """
        plugin_file_content = PluginInfo(plugin_config_file, hooks_available=None)
        content_version = plugin_file_content.version.base_version
        semantic_version_re = re.compile(r"^(\d+)\.(\d+)\.(\d+)")  # Ex.: 1.0.0 or 2025.1.0
        version = semantic_version_re.match(content_version)

        if not version:
            raise ValueError(
                f"Version attribute does not follow the calendar or semantic versioning, got {content_version!r}"
            )

    def _hook_specs_header_content(self, plugin_id: str) -> str:
        """
        Create a C header file with the content informed on the hook_specs
        """
        list_with_hook_specs_with_documentation = ""

        for hook in self.hooks:
            hook_specs_content = "\n/*!\n"
            hook_specs_content += hook.documentation
            hook_specs_content += dedent(
                f"""
            */
            #define HOOK_{hook.macro_name}({hook.args}) HOOKMAN_API_EXP {hook.r_type} HOOKMAN_FUNC_EXP {hook.function_name}({hook.args_with_type})
            """
            )
            list_with_hook_specs_with_documentation += hook_specs_content

        file_content = dedent(
            f"""\
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

        HOOKMAN_API_EXP const char* HOOKMAN_FUNC_EXP get_plugin_id() {{
            return \"{plugin_id}\";
        }}

        """
        )
        file_content += list_with_hook_specs_with_documentation
        file_content += dedent(
            f"""

        #endif // {self.project_name.upper()}_HOOK_SPECS_HEADER_FILE
        """
        )
        return file_content

    _DO_NOT_MODIFY_MSG = "File automatically generated by hookman, **DO NOT MODIFY MANUALLY**"

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
            "#include <map>",
            "",
            "#ifdef _WIN32",
            "    #include <cstdlib>",
            "    #include <windows.h>",
            "#else",
            "    #include <dlfcn.h>",
            "#endif",
            "",
        ]
        content_lines += (f"#include <{x}>" for x in self.extra_includes)
        content_lines += [
            "",
            "namespace hookman {",
            "",
            "template <typename F_TYPE> std::function<F_TYPE> from_c_pointer(uintptr_t p) {",
            "    return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));",
            "}",
            "",
            "class HookCaller {",
            "public:",
        ]

        for hook in self.hooks:
            list_with_hook_calls += [
                f"    std::vector<std::function<{hook.r_type}({hook.args_type})>> {hook.name}_impls() {{",
                f"        return this->_{hook.name}_impls;",
                "    }",
                f"    std::function<{hook.r_type}({hook.args_type})> {hook.name}_impl(const std::string &plugin_id) {{",
                f"        return this->_{hook.name}_map[plugin_id];",
                "    }",
            ]
            list_with_private_members += [
                f"    std::vector<std::function<{hook.r_type}({hook.args_type})>> _{hook.name}_impls;",
                f"    std::map<std::string, std::function<{hook.r_type}({hook.args_type})>> _{hook.name}_map;",
            ]

            list_with_set_functions += [
                # uintptr overload
                f"    void append_{hook.name}_impl(uintptr_t pointer, const std::string &plugin_id) {{",
                f"        this->_{hook.name}_impls.push_back(from_c_pointer<{hook.r_type}({hook.args_type})>(pointer));",
                f"        this->_{hook.name}_map[plugin_id] = from_c_pointer<{hook.r_type}({hook.args_type})>((uintptr_t)(pointer));",
                "    }",
                "",
                # std::function overload
                f"    void append_{hook.name}_impl(std::function<{hook.r_type}({hook.args_type})> func, const std::string &plugin_id) {{",
                f"        this->_{hook.name}_impls.push_back(func);",
                f"        this->_{hook.name}_map[plugin_id] = func;",
                "    }",
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
        content_lines.append("")

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
        signatures = {(x.r_type, x.args_type) for x in self.hooks}
        for r_type, args_type in sorted(signatures):
            content_lines.append(
                f"PYBIND11_MAKE_OPAQUE(std::vector<std::function<{r_type}({args_type})>>);"
            )
        content_lines.append("")

        content_lines.append(f"PYBIND11_MODULE({self.pyd_name}, m) {{")

        for index, (r_type, args_type) in enumerate(sorted(signatures)):
            name = f"vector_hook_impl_type_{index}"
            vector_type = f"std::vector<std::function<{r_type}({args_type})>>"
            content_lines.append(
                f'    py::bind_vector<{vector_type}>(m, "{name}", "Hook for vector implementation type {index}");'
            )
        content_lines.append("")

        content_lines += [
            '    py::class_<hookman::HookCaller>(m, "HookCaller")',
            "        .def(py::init<>())",
            '        .def("load_impls_from_library", &hookman::HookCaller::load_impls_from_library)',
        ]
        for hook in self.hooks:
            append_ptr = f"&hookman::HookCaller::append_{hook.name}_impl"
            append_uint_sig = "void (hookman::HookCaller::*)(uintptr_t, const std::string&)"
            append_function_sig = f"void (hookman::HookCaller::*)(std::function<{hook.r_type}({hook.args_type})>, const std::string&)"

            content_lines += [
                f'        .def("{hook.name}_impls", &hookman::HookCaller::{hook.name}_impls)',
                f'        .def("{hook.name}_impl", &hookman::HookCaller::{hook.name}_impl)',
                f'        .def("append_{hook.name}_impl", ({append_uint_sig}) {append_ptr})',
                f'        .def("append_{hook.name}_impl", ({append_function_sig}) {append_ptr})',
            ]
        content_lines.append("    ;")
        content_lines.append("}")
        content_lines.append("")
        return "\n".join(content_lines)

    def _generate_cmake_files(self, dst_path: Path) -> None:
        from textwrap import dedent

        hook_caller_hpp = Path(dst_path / "cpp" / "CMakeLists.txt")
        with open(hook_caller_hpp, mode="w") as file:
            file.writelines(
                dedent(
                    f"""\
                add_library({self.pyd_name}_interface INTERFACE)
                target_include_directories({self.pyd_name}_interface INTERFACE ./)
                """
                )
            )

        if self.pyd_name:
            hook_caller_python = Path(dst_path / "binding" / "CMakeLists.txt")
            with open(hook_caller_python, mode="w") as file:
                file.writelines(
                    dedent(
                        f"""\
                find_package(pybind11 REQUIRED)

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
                """
                    )
                )

    def _plugin_config_file_content(
        self,
        caption: str,
        plugin_id: str,
        author_email: str,
        author_name: str,
        extras: Mapping[str, str] | None,
        requirements: Mapping[str, str] | None,
    ) -> str:
        """
        Return a string that represent the content of a valid configuration for a plugin
        """
        import strictyaml

        file_content = dedent(
            f"""\
        author: '{author_name}'
        caption: '{caption}'
        email: '{author_email}'
        id: '{plugin_id}'
        version: '1.0.0'
        """
        )
        if extras is not None:
            extras_dict = {"extras": extras}
            file_content += strictyaml.as_document(extras_dict).as_yaml()

        if requirements is not None:
            requirement_dict = {"requirements": dict(sorted(requirements.items()))}
            file_content += strictyaml.as_document(requirement_dict).as_yaml()

        return file_content

    def _readme_content(self, caption: str, author_email: str, author_name: str) -> str:
        return dedent(
            f"""\
        Plugin: '{caption}'
        Author: '{author_name}'
        Email: '{author_email}'

        This is a sample readme file with the supported syntax, the content of this file should be write in markdown.

        You can find an overview of the valid tags that can be used to write the content of this file on the following link:
        https://guides.github.com/features/mastering-markdown/#syntax
        """
        )

    def _generate_rst_title(self, caption: str) -> str:
        complement = " Changelog"
        title = caption + complement
        border = "=" * (len(title))
        return f"""{border}
        {title}
        {border}
        """

    def _changelog_content(self, caption: str) -> str:
        return dedent(
            f"""\
        {self._generate_rst_title(caption)}
        1.0.0 (Unreleased)
        ==================

        Major highlights
        ------------------

        * Example feature A
        """
        )

    def _plugin_source_content(
        self, extra_includes: list[str], extra_body_lines: list[str], exclude_hooks: list[str]
    ) -> str:
        """
        Create a C header file with the content informed on the hook_specs

        :param extra_includes: All includes extras, requested to be included, example, the include of a SDK.
        :param extra_body_lines: Extra lines, indent to be inserted on the template, example, implementation of hook.
        :param exclude_hooks: List of hooks names, that will not be inserted on the source file
        """

        plugin_hooks_macro = [
            f"// HOOK_{hook.macro_name}({hook.args}){{}}"
            for hook in self.hooks
            if hook.macro_name not in exclude_hooks
        ]
        file_content = ['#include "hook_specs.h"', "\n"]
        extra_include_content = [f"#include {include}" for include in extra_includes]
        full_content = (
            extra_include_content + file_content + extra_body_lines + plugin_hooks_macro + [""]
        )
        return "\n".join(full_content)

    def _plugin_cmake_file_content(self, plugin_id: str) -> str:
        return dedent(
            f"""\
            cmake_minimum_required(VERSION 3.5.2)

            set(PROJECT_NAME {plugin_id})
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

            project ({plugin_id} LANGUAGES CXX C)
            add_subdirectory(src)
        """
        )

    def _plugin_src_cmake_file_content(self, plugin_id: str) -> str:
        return dedent(
            f"""\
            add_library({plugin_id} SHARED {plugin_id}.cpp hook_specs.h)
            target_include_directories({plugin_id} PUBLIC ${{SDK_INCLUDE_DIR}})
            install(TARGETS {plugin_id} EXPORT ${{PROJECT_NAME}}_export DESTINATION ${{ARTIFACTS_DIR}})
        """
        )

    def _compile_shared_lib_python_script_content(self, plugin_id: str) -> str:
        lib_name_win = f"{plugin_id}.dll"
        lib_name_linux = f"lib{plugin_id}.so"

        return dedent(
            f"""\
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
                shared_lib_path = artifacts_dir / "{lib_name_win}"
            else:
                shared_lib_path = artifacts_dir / "{lib_name_linux}"

            if build_dir.exists():
                shutil.rmtree(build_dir)

            build_dir.mkdir()

            binary_directory_path = f"-B{{str(build_dir)}}"
            home_directory_path = f"-H{{current_dir}}"
            sdk_include_dir = f"-DSDK_INCLUDE_DIR={{os.getenv('SDK_INCLUDE_DIR', '')}}"
            build_generator = "Visual Studio 14 2015 Win64" if sys.platform == "win32" else "Unix Makefiles"
            if artifacts_dir.exists():
                shutil.rmtree(artifacts_dir)

            subprocess.check_call(["cmake", binary_directory_path, home_directory_path, sdk_include_dir, "-G", build_generator])
            subprocess.check_call(["cmake", "--build", str(build_dir), "--config", "Release", "--target", "install"])

            if package_dir.exists():
                shutil.rmtree(package_dir)

            shutil.copytree(src=assets, dst=package_dir)
            shutil.copy2(src=shared_lib_path, dst=package_dir)
        """
        )


def _generate_load_function(hooks: list[Hook]) -> list[str]:
    result = ["#if defined(_WIN32)", ""]
    result += _generate_windows_body(hooks)
    result += ["", "#elif defined(__linux__)", ""]
    result += _generate_linux_body(hooks)
    result += ["", "#else", '    #error "unknown platform"', "#endif", ""]
    return result


def _generate_windows_body(hooks: list[Hook]) -> list[str]:
    """Generate Windows specific functions.

    At the moment it implements load_impls_from_library, class destructor, and an utility function
    to convert from utf8 to wide-strings so we can use the wide family of windows
    functions that accept unicode.
    """
    # generate destructor to free the library handles opened by load_from_library()
    result = [
        "public:",
        "    ~HookCaller() {",
        "        for (auto handle : this->handles) {",
        "            FreeLibrary(handle);",
        "        }",
        "    }",
    ]

    # generate load_impls_from_library()
    result += [
        "    void load_impls_from_library(const std::string& utf8_filename, const std::string& plugin_id) {",
        "        std::wstring w_filename = utf8_to_wstring(utf8_filename);",
        "        auto handle = this->load_dll(w_filename);",
        "        if (handle == NULL) {",
        '            throw std::runtime_error("Error loading library " + utf8_filename + ": " + std::to_string(GetLastError()));',
        "        }",
        "        this->handles.push_back(handle);",
        "",
    ]

    for index, hook in enumerate(hooks):
        result += [
            f'        auto p{index} = GetProcAddress(handle, "{hook.function_name}");',
            f"        if (p{index} != nullptr) {{",
            f"            this->append_{hook.name}_impl((uintptr_t)(p{index}), plugin_id);",
            "        }",
            "",
        ]
    result.append("    }")

    result += [
        "",
        "",
        "private:",
        "    std::wstring utf8_to_wstring(const std::string& s) {",
        "        int flags = 0;",
        "        int required_size = MultiByteToWideChar(CP_UTF8, flags, s.c_str(), -1, nullptr, 0);",
        "        std::wstring result;",
        "        if (required_size == 0) {",
        "            return result;",
        "        }",
        "        result.resize(required_size);",
        "        int err = MultiByteToWideChar(CP_UTF8, flags, s.c_str(), -1, &result[0], required_size);",
        "        if (err == 0) {",
        "            // error handling: https://docs.microsoft.com/en-us/windows/desktop/api/stringapiset/nf-stringapiset-multibytetowidechar#return-value",
        "            switch (GetLastError()) {",
        '                case ERROR_INSUFFICIENT_BUFFER: throw std::runtime_error("utf8_to_wstring: ERROR_INSUFFICIENT_BUFFER");',
        '                case ERROR_INVALID_FLAGS: throw std::runtime_error("utf8_to_wstring: ERROR_INVALID_FLAGS");',
        '                case ERROR_INVALID_PARAMETER: throw std::runtime_error("utf8_to_wstring: ERROR_INVALID_PARAMETER");',
        '                case ERROR_NO_UNICODE_TRANSLATION: throw std::runtime_error("utf8_to_wstring: ERROR_NO_UNICODE_TRANSLATION");',
        '                default: throw std::runtime_error("Undefined error: " + std::to_string(GetLastError()));',
        "            }",
        "        }",
        "        return result;",
        "    }",
        "",
        "",
        "    class PathGuard {",
        "    public:",
        "        explicit PathGuard(std::wstring filename)",
        "            : path_env{ get_path() }",
        "        {",
        r'            std::wstring::size_type dir_name_size = filename.find_last_of(L"/\\");',
        '            std::wstring new_path_env = path_env + L";" + filename.substr(0, dir_name_size);',
        '            _wputenv_s(L"PATH", new_path_env.c_str());',
        "        }",
        "",
        "        ~PathGuard() {",
        '            _wputenv_s(L"PATH", path_env.c_str());',
        "        }",
        "",
        "    private:",
        "        static std::wstring get_path() {",
        "            rsize_t _len = 0;",
        "            wchar_t *buf;",
        '            _wdupenv_s(&buf, &_len, L"PATH");',
        "            std::wstring path_env{ buf };",
        "            free(buf);",
        "            return path_env;",
        "        } ",
        "",
        "        std::wstring path_env;",
        "    };",
        "",
        "    HMODULE load_dll(const std::wstring& filename) {",
        "        // Path Modifier",
        "        PathGuard path_guard{ filename };",
        "        // Load library (DLL)",
        "        return LoadLibraryW(filename.c_str());",
        "    }",
        "",
        "",
        "private:",
        "    std::vector<HMODULE> handles;",
    ]
    return result


def _generate_linux_body(hooks: list[Hook]) -> list[str]:
    """
    Generate linux specific functions.

    At the moment it implements load_impls_from_library and the class destructor
    to cleanup handles.
    """
    # generate destructor to free the library handles opened by load_from_library()
    result = [
        "private:",
        "    std::vector<void*> handles;",
        "",
        "public:",
        "    ~HookCaller() {",
        "        for (auto handle : this->handles) {",
        "            dlclose(handle);",
        "        }",
        "    }",
    ]

    # generate load_impls_from_library()
    result += [
        "    void load_impls_from_library(const std::string& utf8_filename, const std::string& plugin_id) {",
        "        auto handle = dlopen(utf8_filename.c_str(), RTLD_LAZY);",
        "        if (handle == nullptr) {",
        '            throw std::runtime_error("Error loading library " + utf8_filename + ": dlopen failed");',
        "        }",
        "        this->handles.push_back(handle);",
        "",
    ]

    for index, hook in enumerate(hooks):
        result += [
            f'        auto p{index} = dlsym(handle, "{hook.function_name}");',
            f"        if (p{index} != nullptr) {{",
            f"            this->append_{hook.name}_impl((uintptr_t)(p{index}), plugin_id);",
            "        }",
            "",
        ]
    result.append("    }")
    return result
