import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.storage.db import storage_repo

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


@pytest.fixture
def client():
    # Clear in-memory repo before each test
    storage_repo.clear()
    with TestClient(app) as test_client:
        yield test_client
    storage_repo.clear()


@pytest.fixture
def sample_kml_path():
    return SAMPLE_DIR / "sample_polygon.kml"


@pytest.fixture
def sample_linestring_kml_path():
    return SAMPLE_DIR / "sample_linestring.kml"


@pytest.fixture
def sample_points_kml_path():
    return SAMPLE_DIR / "sample_points.kml"


@pytest.fixture
def sample_shapefile_zip_path():
    return SAMPLE_DIR / "sample_shapefile.zip"
