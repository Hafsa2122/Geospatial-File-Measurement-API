import pytest
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, GeometryCollection
from app.services.crs_transformer import CRSTransformer
from app.services.measurement import MeasurementService
from app.models.schemas import MeasurementType


def test_utm_zone_calculation():
    # New York City: lon -73.96, lat 40.78 -> UTM Zone 18N (EPSG:32618)
    utm_ny = CRSTransformer.get_optimal_utm_crs(-73.96, 40.78)
    assert utm_ny == "EPSG:32618"

    # Paris, France: lon 2.35, lat 48.85 -> UTM Zone 31N (EPSG:32631)
    utm_paris = CRSTransformer.get_optimal_utm_crs(2.35, 48.85)
    assert utm_paris == "EPSG:32631"

    # Sydney, Australia: lon 151.20, lat -33.86 -> UTM Zone 56S (EPSG:32756)
    utm_sydney = CRSTransformer.get_optimal_utm_crs(151.20, -33.86)
    assert utm_sydney == "EPSG:32756"


def test_polygon_area_measurement():
    # 1 degree x 1 degree box at equator in EPSG:4326 (approx ~12,300 sq km)
    poly = Polygon([(0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)])
    meas, proj_crs = MeasurementService.calculate_measurement(poly, "EPSG:4326")
    
    assert meas.type == MeasurementType.AREA
    assert meas.unit == "square_meters"
    assert meas.value is not None
    assert meas.value > 0
    assert "m²" in meas.formatted
    assert "hectares" in meas.conversions
    assert proj_crs.startswith("EPSG:326")


def test_linestring_length_measurement():
    # Line along meridian in EPSG:4326 (~1.11 km for 0.01 deg)
    line = LineString([(0.0, 0.0), (0.0, 0.01)])
    meas, proj_crs = MeasurementService.calculate_measurement(line, "EPSG:4326")

    assert meas.type == MeasurementType.LENGTH
    assert meas.unit == "meters"
    assert meas.value is not None
    assert 1000 < meas.value < 1200  # Approx 1110 meters
    assert "m" in meas.formatted
    assert "kilometers" in meas.conversions


def test_point_measurement():
    pt = Point(-73.9857, 40.7484)
    meas, proj_crs = MeasurementService.calculate_measurement(pt, "EPSG:4326")

    assert meas.type == MeasurementType.NONE
    assert meas.value is None
    assert meas.unit is None


def test_empty_and_unsupported_geometry():
    empty_poly = Polygon()
    meas, _ = MeasurementService.calculate_measurement(empty_poly, "EPSG:4326")
    assert meas.type == MeasurementType.NONE

    gc = GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])])
    meas_gc, _ = MeasurementService.calculate_measurement(gc, "EPSG:4326")
    assert meas_gc.type == MeasurementType.UNSUPPORTED
