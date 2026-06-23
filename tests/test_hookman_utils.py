# mypy: allow-untyped-defs
import os
import sys

import pytest

from hookman.exceptions import SharedLibraryLoadError
from hookman.hookman_utils import change_path_env
from hookman.hookman_utils import find_config_files
from hookman.hookman_utils import load_shared_lib


def test_find_config_files(datadir) -> None:
    config_files = find_config_files(datadir)
    assert len(config_files) == 2

    config_files = find_config_files(datadir, ignored_sub_dir_names=["fizzbuzz"])
    assert len(config_files) == 2

    config_files = find_config_files(datadir, ignored_sub_dir_names=["foo"])
    assert len(config_files) == 1

    config_files = find_config_files(datadir, ignored_sub_dir_names=["foo", "bar"])
    assert len(config_files) == 0

    config_files = find_config_files([datadir / "non_existing_folder"])
    assert len(config_files) == 0


@pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="path only needs changing on Windows"
)
def test_change_path_env(simple_plugin_dll) -> None:
    dll_dir = str(simple_plugin_dll.parent)
    assert dll_dir not in os.environ["PATH"]
    with change_path_env(str(simple_plugin_dll)):
        assert dll_dir in os.environ["PATH"]
    assert dll_dir not in os.environ["PATH"]


@pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="path only needs changing on Windows"
)
def test_path_change_when_load_library(simple_plugin_dll, mocker) -> None:
    mocked = mocker.patch("hookman.hookman_utils.change_path_env")

    with load_shared_lib(str(simple_plugin_dll)):
        pass
    mocked.assert_called_once()


def test_load_shared_lib_raises_shared_library_load_error_for_corrupt_file(tmp_path) -> None:
    """A file that exists but is not a valid shared library raises SharedLibraryLoadError."""

    lib_name = "my_plugin.dll" if sys.platform == "win32" else "libmy_plugin.so"
    corrupt_lib = tmp_path / lib_name
    corrupt_lib.write_text("not a real shared library")

    with pytest.raises(SharedLibraryLoadError) as exc_info:
        with load_shared_lib(str(corrupt_lib)):
            pass  # pragma: no cover

    assert exc_info.value.shared_lib_path == corrupt_lib
    assert exc_info.value.reason  # Non-empty OS-dependent error description.
