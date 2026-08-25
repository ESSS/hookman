"""
Build a human-readable diagnostic block for shared library load failures.

This is intentionally separate from `hookman_utils.py`: the formatting logic here does
not itself load any shared library, which keeps it easy to unit test in isolation.

The block is meant to answer the question that ASIM-6769 took manual investigation to
answer: *why* did the OS loader resolve the wrong copy of a dependency DLL. The most
common cause observed so far is a conflicting Python distribution (e.g. Anaconda) placed
earlier on `PATH` than the plugin's own `artifacts/` directory, shadowing one of the
plugin's bundled dependencies.
"""

import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from typing_extensions import Self

#: Directories explicitly registered via `os.add_dll_directory` by this process,
#: in registration order. `os` provides no API to enumerate them, so callers that add
#: directories to the DLL search path are expected to also record them here via
#: `register_dll_directory`.
_REGISTERED_DLL_DIRECTORIES: list[Path] = []


def register_dll_directory(directory: Path) -> None:
    """
    Record *directory* as having been added to the DLL search path.

    Callers of `os.add_dll_directory` (both within hookman and in downstream projects
    such as alfasim) should call this alongside it, so that `LoadDiagnostics` can
    report the full set of registered directories.

    *directory* is resolved before storing, so the same directory reached through a
    relative path or a symlink from different call sites is still deduplicated to a
    single entry.

    Idempotent: registering the same directory twice keeps a single entry.
    """
    resolved_directory = directory.resolve()
    if resolved_directory not in _REGISTERED_DLL_DIRECTORIES:
        _REGISTERED_DLL_DIRECTORIES.append(resolved_directory)


def registered_dll_directories() -> Sequence[Path]:
    """
    Return the directories registered so far via `register_dll_directory`, in
    registration order.
    """
    return tuple(_REGISTERED_DLL_DIRECTORIES)


def reset_registered_dll_directories() -> None:
    """
    Clear the registered-directories registry.

    Intended for test isolation (this module-level state otherwise leaks between
    tests within the same process); production code has no reason to call this, since
    the registry is meant to reflect the process's DLL search directories for its
    whole lifetime.
    """
    _REGISTERED_DLL_DIRECTORIES.clear()


def search_env_var_name() -> str:
    """
    Name of the environment variable the OS loader consults to resolve a shared
    library's dependencies: `PATH` on Windows, `LD_LIBRARY_PATH` on POSIX (mirrors the
    platform split in the generated C++ `load_impls_from_library`).
    """
    return "PATH" if sys.platform.startswith("win") else "LD_LIBRARY_PATH"


def search_directories() -> Sequence[Path]:
    """
    Return the effective library search directories, in search order, as given by the
    OS: `PATH` entries on Windows, `LD_LIBRARY_PATH` entries on POSIX.

    Entries are not deduplicated or filtered, mirroring how the OS loader consults
    the variable (empty entries from stray path-separators are dropped).
    """
    path_env = os.environ.get(search_env_var_name(), "")
    return [Path(entry) for entry in path_env.split(os.pathsep) if entry]


@dataclass(frozen=True)
class ShadowedLibrary:
    """A library bundled with the plugin that is shadowed by a same-named file earlier
    in the OS loader's search directories (`PATH` on Windows, `LD_LIBRARY_PATH` on
    POSIX)."""

    library_name: str
    """Basename of the shadowed library, e.g. ``splog.dll``."""

    found_in: Path
    """Directory earlier than the plugin's own directory in the search order,
    containing a same-named file."""

    plugin_copy: Path
    """Path to the plugin's own copy of the library."""


def _is_shared_library(entry: Path) -> bool:
    """
    True if *entry* looks like a shared library: a `.dll`, or a `.so` optionally
    followed by a version suffix (e.g. `libfoo.so.1.2.3`).
    """
    return entry.suffix.lower() == ".dll" or ".so" in entry.suffixes


def find_shadowing_libraries(shared_lib_path: Path) -> Sequence[ShadowedLibrary]:
    """
    Find libraries bundled alongside *shared_lib_path* that are shadowed by a same-named
    file in an earlier search directory (see `search_env_var_name`).

    This is the check that would have flagged ASIM-6769: the plugin's ``artifacts/``
    directory bundles its own ``splog.dll``, but an `anaconda3` directory earlier on
    `PATH` contains a different, incompatible ``splog.dll`` that the loader resolves
    first.

    :param shared_lib_path:
        Path to the plugin's main shared library; its siblings in the same directory
        are the ones checked for shadowing.
    """
    plugin_dir = shared_lib_path.parent
    if not plugin_dir.is_dir():
        return []

    bundled_library_names = sorted(
        entry.name
        for entry in plugin_dir.iterdir()
        if entry.is_file() and _is_shared_library(entry)
    )
    if not bundled_library_names:
        return []

    shadowed: list[ShadowedLibrary] = []
    for directory in search_directories():
        if directory == plugin_dir:
            # The plugin's own directory does not shadow itself; entries after this
            # point in PATH are irrelevant too, since the plugin's directory is added
            # ahead of them for this very load (see `change_path_env`).
            break
        if not directory.is_dir():
            continue
        for library_name in bundled_library_names:
            if (directory / library_name).is_file():
                shadowed.append(
                    ShadowedLibrary(
                        library_name=library_name,
                        found_in=directory,
                        plugin_copy=plugin_dir / library_name,
                    )
                )
    return shadowed


@dataclass(frozen=True)
class LoadDiagnostics:
    """
    Structured breakdown of the DLL search environment at load time.

    Kept separate from the plain-string `reason` on `SharedLibraryLoadError` /
    `PluginLoadFailure` so a caller can inspect the individual fields (e.g. which
    library was shadowed and by what directory) instead of having to parse `str(self)`
    back apart. `str(self)` still renders the same block a caller only interested in
    display can just log or show as-is.
    """

    shadowed_libraries: Sequence[ShadowedLibrary]
    """Bundled libraries shadowed by a same-named file earlier on `PATH`."""

    registered_dll_directories: Sequence[Path]
    """Directories added via `os.add_dll_directory` over the process lifetime."""

    path_entries: Sequence[Path]
    """The effective library search directories, in search order (`PATH` entries on
    Windows, `LD_LIBRARY_PATH` entries on POSIX)."""

    collection_error: str = ""
    """Set instead of raising when gathering the diagnostics itself fails (e.g. a
    permission error walking a `PATH` directory), so a bug here can never mask the
    original load error. When set, the other fields are empty and `str(self)` reports
    this instead of the normal block."""

    @classmethod
    def collect(cls, shared_lib_path: Path) -> Self:
        """
        Collect the `LoadDiagnostics` explaining the DLL search environment for
        *shared_lib_path*.

        Gathers, in order of actionability: same-named libraries shadowing one of the
        plugin's own files earlier on `PATH`, the directories explicitly registered via
        `os.add_dll_directory`, and the full `PATH` listing.

        Never raises: any failure while gathering this information is reported via
        `collection_error` so it can never mask the original load error. Callers with
        nothing to diagnose (e.g. no load was attempted) should use `None` instead of
        calling this.
        """
        try:
            return cls(
                shadowed_libraries=tuple(find_shadowing_libraries(shared_lib_path)),
                registered_dll_directories=tuple(_REGISTERED_DLL_DIRECTORIES),
                path_entries=tuple(search_directories()),
            )
        except Exception as error:  # noqa: BLE001 - diagnostics must never break error reporting
            return cls(
                shadowed_libraries=(),
                registered_dll_directories=(),
                path_entries=(),
                collection_error=str(error),
            )

    def __str__(self) -> str:
        if self.collection_error:
            return f"(failed to collect diagnostics: {self.collection_error})"

        sections: list[str] = []

        if self.shadowed_libraries:
            lines = [
                f"  - {entry.library_name} in {entry.found_in}\n"
                f"    (plugin also ships {entry.plugin_copy})"
                for entry in self.shadowed_libraries
            ]
            sections.append(
                "Possible conflicting libraries found earlier in the search path:\n"
                + "\n".join(lines)
            )

        if self.registered_dll_directories:
            lines = [
                f"  {i}. {directory}"
                for i, directory in enumerate(self.registered_dll_directories, 1)
            ]
            sections.append("DLL search directories (os.add_dll_directory):\n" + "\n".join(lines))

        path_lines = [
            f"  {i:3d}. {directory}{'' if directory.is_dir() else '  (does not exist)'}"
            for i, directory in enumerate(self.path_entries, 1)
        ]
        sections.append(
            f"{search_env_var_name()} ({len(self.path_entries)} entries):\n" + "\n".join(path_lines)
        )

        return "\n\n".join(sections)
