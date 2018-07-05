from pathlib import Path

import pytest

@pytest.fixture
def libs_path():
    return Path(__file__).parents[1] / 'build/libs'
