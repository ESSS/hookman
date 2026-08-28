# mypy: allow-untyped-defs
import os
import sys

import pytest

from hookman.dll_diagnostics import (
    LoadDiagnostics,
    find_shadowing_libraries,
    register_dll_directory,
    registered_dll_directories,
    reset_registered_dll_directories,
    search_directories,
    search_env_var_name,
)


@pytest.fixture(autouse=True)
def isolate_registered_dll_directories() -> None:
    """Reset the module-level DLL-directory registry so tests don't leak state into
    each other."""
    reset_registered_dll_directories()


def _make_plugin_dir(tmp_path, library_names):
    plugin_dir = tmp_path / "plugin" / "artifacts"
    plugin_dir.mkdir(parents=True)
    for name in library_names:
        (plugin_dir / name).write_text("fake library")
    return plugin_dir


def set_search_path(monkeypatch, value: str) -> None:
    """Set whichever environment variable `search_directories` reads on this platform
    (`PATH` on Windows, `LD_LIBRARY_PATH` on POSIX)."""
    monkeypatch.setenv(search_env_var_name(), value)


@pytest.mark.skipif(sys.platform != "win32", reason="checks the Windows-specific mapping")
def test_search_env_var_name_is_path_on_windows() -> None:
    assert search_env_var_name() == "PATH"


@pytest.mark.skipif(sys.platform == "win32", reason="checks the POSIX-specific mapping")
def test_search_env_var_name_is_ld_library_path_on_posix() -> None:
    assert search_env_var_name() == "LD_LIBRARY_PATH"


def test_search_directories_splits_path(monkeypatch, tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    set_search_path(monkeypatch, f"{first}{os.pathsep}{second}")
    assert list(search_directories()) == [first, second]


def test_search_directories_drops_empty_entries(monkeypatch) -> None:
    set_search_path(monkeypatch, f"{os.pathsep}{os.pathsep}")
    assert search_directories() == []


def test_register_dll_directory_deduplicates_unresolved_and_resolved_forms(tmp_path) -> None:
    """Callers don't agree on whether to resolve before registering (hookman's own
    `change_path_env` doesn't, alfasim's `dll_directory._register` used to) -- the same
    directory reached through either form must still collapse to a single entry
    (ASIM-6857)."""
    real_dir = tmp_path / "artifacts"
    real_dir.mkdir()
    unresolved = tmp_path / "." / "artifacts"

    register_dll_directory(unresolved)
    register_dll_directory(real_dir)

    assert registered_dll_directories() == (real_dir.resolve(),)


def test_find_shadowing_libraries_reports_earlier_same_named_file(monkeypatch, tmp_path) -> None:
    """The scenario behind ASIM-6769: a conflicting copy earlier in the search path
    shadows a library the plugin bundles."""
    plugin_dir = _make_plugin_dir(tmp_path, ["splog.dll"])
    decoy_dir = tmp_path / "anaconda3" / "Library" / "bin"
    decoy_dir.mkdir(parents=True)
    (decoy_dir / "splog.dll").write_text("conflicting library")

    set_search_path(monkeypatch, f"{decoy_dir}{os.pathsep}{plugin_dir}")

    [shadow] = find_shadowing_libraries(plugin_dir / "scaling.dll")
    assert shadow.library_name == "splog.dll"
    assert shadow.found_in == decoy_dir
    assert shadow.plugin_copy == plugin_dir / "splog.dll"


def test_find_shadowing_libraries_ignores_entries_after_plugin_dir(monkeypatch, tmp_path) -> None:
    """A same-named file that comes *after* the plugin's own directory in the search
    path is not a shadowing hit: the plugin's own copy is the one that resolves first."""
    plugin_dir = _make_plugin_dir(tmp_path, ["splog.dll"])
    later_dir = tmp_path / "later"
    later_dir.mkdir()
    (later_dir / "splog.dll").write_text("irrelevant, comes after")

    set_search_path(monkeypatch, f"{plugin_dir}{os.pathsep}{later_dir}")

    assert find_shadowing_libraries(plugin_dir / "scaling.dll") == []


@pytest.mark.skipif(sys.platform == "win32", reason="uses a versioned .so suffix")
def test_find_shadowing_libraries_reports_versioned_so_file(monkeypatch, tmp_path) -> None:
    """A versioned shared object (e.g. `libsplog.so.1.2.3`) is still recognized as a
    bundled library, not just a plain `.so` (ASIM-6857)."""
    plugin_dir = _make_plugin_dir(tmp_path, ["libsplog.so.1.2.3"])
    decoy_dir = tmp_path / "conflicting_install"
    decoy_dir.mkdir()
    (decoy_dir / "libsplog.so.1.2.3").write_text("conflicting library")

    set_search_path(monkeypatch, f"{decoy_dir}{os.pathsep}{plugin_dir}")

    [shadow] = find_shadowing_libraries(plugin_dir / "scaling.so")
    assert shadow.library_name == "libsplog.so.1.2.3"
    assert shadow.found_in == decoy_dir
    assert shadow.plugin_copy == plugin_dir / "libsplog.so.1.2.3"


def test_find_shadowing_libraries_no_conflict(monkeypatch, tmp_path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, ["splog.dll"])
    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()

    set_search_path(monkeypatch, f"{clean_dir}{os.pathsep}{plugin_dir}")

    assert find_shadowing_libraries(plugin_dir / "scaling.dll") == []


@pytest.mark.skipif(sys.platform != "win32", reason="uses .dll as the bundled library suffix")
def test_load_diagnostics_collect_includes_shadowed_libraries_on_windows(
    monkeypatch, tmp_path
) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, ["splog.dll"])
    decoy_dir = tmp_path / "anaconda3"
    decoy_dir.mkdir()
    (decoy_dir / "splog.dll").write_text("conflicting library")

    set_search_path(monkeypatch, f"{decoy_dir}{os.pathsep}{plugin_dir}")

    diagnostics = LoadDiagnostics.collect(plugin_dir / "scaling.dll")

    # Structured fields are inspectable directly, without parsing str(diagnostics).
    [shadow] = diagnostics.shadowed_libraries
    assert shadow.library_name == "splog.dll"
    assert shadow.found_in == decoy_dir
    assert diagnostics.path_entries == (decoy_dir, plugin_dir)
    assert diagnostics.collection_error == ""

    # str() still renders the same block callers only interested in display can log.
    block = str(diagnostics)
    assert "Possible conflicting libraries found earlier in the search path" in block
    assert "splog.dll" in block
    assert str(decoy_dir) in block
    assert "PATH (2 entries)" in block
    assert str(plugin_dir) in block


@pytest.mark.skipif(sys.platform == "win32", reason="uses .so as the bundled library suffix")
def test_load_diagnostics_collect_includes_shadowed_libraries_on_posix(
    monkeypatch, tmp_path
) -> None:
    """POSIX equivalent of the Windows test above: the shadowing search reads
    `LD_LIBRARY_PATH`, not `PATH` (ASIM-6857)."""
    plugin_dir = _make_plugin_dir(tmp_path, ["splog.so"])
    decoy_dir = tmp_path / "conflicting_install"
    decoy_dir.mkdir()
    (decoy_dir / "splog.so").write_text("conflicting library")

    set_search_path(monkeypatch, f"{decoy_dir}{os.pathsep}{plugin_dir}")

    diagnostics = LoadDiagnostics.collect(plugin_dir / "scaling.so")

    [shadow] = diagnostics.shadowed_libraries
    assert shadow.library_name == "splog.so"
    assert shadow.found_in == decoy_dir
    assert diagnostics.path_entries == (decoy_dir, plugin_dir)
    assert diagnostics.collection_error == ""

    block = str(diagnostics)
    assert "Possible conflicting libraries found earlier in the search path" in block
    assert "splog.so" in block
    assert str(decoy_dir) in block
    assert "LD_LIBRARY_PATH (2 entries)" in block
    assert str(plugin_dir) in block


def test_load_diagnostics_collect_omits_shadow_section_when_clean(monkeypatch, tmp_path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, ["splog.dll"])
    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()

    set_search_path(monkeypatch, f"{clean_dir}{os.pathsep}{plugin_dir}")

    diagnostics = LoadDiagnostics.collect(plugin_dir / "scaling.dll")

    assert diagnostics.shadowed_libraries == ()
    block = str(diagnostics)
    assert "Possible conflicting libraries" not in block
    assert f"{search_env_var_name()} (2 entries)" in block


def test_load_diagnostics_collect_marks_nonexistent_path_entries(monkeypatch, tmp_path) -> None:
    plugin_dir = _make_plugin_dir(tmp_path, [])
    missing_dir = tmp_path / "does_not_exist"

    set_search_path(monkeypatch, f"{missing_dir}{os.pathsep}{plugin_dir}")

    diagnostics = LoadDiagnostics.collect(plugin_dir / "scaling.dll")

    # Existence is a caller-side check, not snapshotted on the entry itself.
    assert missing_dir in diagnostics.path_entries
    assert not missing_dir.is_dir()
    assert f"{missing_dir}  (does not exist)" in str(diagnostics)


def test_load_diagnostics_collect_never_raises(monkeypatch, tmp_path) -> None:
    """A failure while gathering diagnostics is captured as `collection_error` instead
    of propagating, so it can never mask the original load error."""

    def _boom(_shared_lib_path):
        raise RuntimeError("boom")

    monkeypatch.setattr("hookman.dll_diagnostics.find_shadowing_libraries", _boom)

    diagnostics = LoadDiagnostics.collect(tmp_path / "scaling.dll")

    assert diagnostics.collection_error == "boom"
    assert diagnostics.shadowed_libraries == ()
    assert "failed to collect diagnostics" in str(diagnostics)


def test_load_diagnostics_collect_returns_the_concrete_subclass(tmp_path) -> None:
    """`collect()` returns `Self`, so a caller gets a `LoadDiagnostics` back, not some
    other type -- a simple regression guard for the classmethod's return type."""
    diagnostics = LoadDiagnostics.collect(tmp_path / "scaling.dll")
    assert isinstance(diagnostics, LoadDiagnostics)
