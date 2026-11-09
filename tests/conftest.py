import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.datos_sinteticos import crear_archivos  # noqa: E402


@pytest.fixture(scope="session")
def archivos_sinteticos(tmp_path_factory):
    return crear_archivos(tmp_path_factory.mktemp("sinteticos"))
