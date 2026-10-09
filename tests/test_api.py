import io
import zipfile
import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "/docs" in data["documentation"]


def test_upload_kml_polygon(client: TestClient, sample_kml_path):
    with open(sample_kml_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_polygon.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sample_polygon.kml"
    assert data["feature_count"] >= 1
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # 1. Test Get File Info
    info_resp = client.get(f"/api/files/{file_id}/")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert info_data["id"] == file_id
    assert info_data["filename"] == "sample_polygon.kml"

    # 2. Test Get File Measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["id"] == file_id
    assert len(meas_data["features"]) >= 1
    assert meas_data["summary"]["total_area_sq_m"] > 0

    first_feat = meas_data["features"][0]
    assert first_feat["geometry_type"] == "Polygon"
    assert first_feat["measurement"]["type"] == "area"
    assert first_feat["measurement"]["value"] > 0
    assert first_feat["measurement"]["unit"] == "square_meters"


def test_upload_shapefile_zip(client: TestClient, sample_shapefile_zip_path):
    with open(sample_shapefile_zip_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_shapefile.zip", f, "application/zip")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "sample_shapefile.zip"
    assert data["feature_count"] == 2
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # Verify measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["summary"]["total_area_sq_m"] > 0
    assert len(meas_data["features"]) == 2
    # Verify attributes extracted
    assert "plot_id" in meas_data["features"][0]["properties"]


def test_upload_invalid_extension(client: TestClient):
    fake_txt = io.BytesIO(b"Hello world")
    response = client.post(
        "/api/files/",
        files={"file": ("test.txt", fake_txt, "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_zip_without_shp(client: TestClient):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("readme.txt", "No shapefile here")
    zip_buffer.seek(0)

    response = client.post(
        "/api/files/",
        files={"file": ("empty.zip", zip_buffer, "application/zip")},
    )
    assert response.status_code == 400
    assert "does not contain any .shp" in response.json()["detail"]


def test_get_nonexistent_file(client: TestClient):
    response = client.get("/api/files/nonexistent_id/")
    assert response.status_code == 404


def test_delete_file(client: TestClient, sample_kml_path):
    with open(sample_kml_path, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("sample_polygon.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    file_id = upload_resp.json()["id"]

    del_resp = client.delete(f"/api/files/{file_id}/")
    assert del_resp.status_code == 200

    # Ensure it is now 404
    get_resp = client.get(f"/api/files/{file_id}/")
    assert get_resp.status_code == 404
