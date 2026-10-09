import os
import zipfile
import shutil
import tempfile
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import geopandas as gpd
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
import numpy as np
import pandas as pd
from fastkml import kml
import xml.etree.ElementTree as ET

from app.models.schemas import FeatureMeasurement, MeasurementSummary, MeasurementType
from app.services.crs_transformer import CRSTransformer
from app.services.measurement import MeasurementService


def sanitize_value(val: Any) -> Any:
    """Converts numpy / pandas / non-serializable objects into standard JSON-serializable types."""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    return str(val) if not isinstance(val, (str, int, float, bool, list, dict)) else val


class FileProcessorService:
    """
    Service to process geospatial files (.zip shapefiles and .kml files),
    extract features, geometry, attributes, CRS, and compute measurements.
    """

    @classmethod
    def process_file(
        cls, file_path: Path, filename: str
    ) -> Tuple[str, int, List[FeatureMeasurement], MeasurementSummary]:
        """
        Main entrypoint to route file by extension and process features.
        Returns: (file_crs, feature_count, features_list, summary)
        """
        ext = file_path.suffix.lower()
        if ext == ".zip":
            return cls._process_shapefile_zip(file_path)
        elif ext == ".kml":
            return cls._process_kml(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Only .zip (Shapefiles) and .kml are supported.")

    @classmethod
    def _process_shapefile_zip(
        cls, zip_path: Path
    ) -> Tuple[str, int, List[FeatureMeasurement], MeasurementSummary]:
        """
        Unzips archive, locates .shp file, parses features and measurements via GeoPandas.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="shp_extract_"))
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)

            # Locate .shp files
            shp_files = list(temp_dir.rglob("*.shp"))
            if not shp_files:
                raise ValueError("The provided .zip archive does not contain any .shp (Shapefile) file.")

            shp_file = shp_files[0]
            gdf = gpd.read_file(shp_file)

            # Determine CRS
            crs_str = CRSTransformer.normalize_crs(gdf.crs)

            features: List[FeatureMeasurement] = []
            total_area = 0.0
            total_length = 0.0
            type_breakdown: Dict[str, int] = {}
            measured_count = 0

            # Exclude geometry column from properties
            prop_cols = [col for col in gdf.columns if col != gdf.geometry.name]

            for idx, row in gdf.iterrows():
                geom: Optional[BaseGeometry] = row.get(gdf.geometry.name)
                
                if geom is None or geom.is_empty:
                    geom_type = "None"
                    geom_geojson = None
                    meas_detail, proj_crs = MeasurementService.calculate_measurement(None, crs_str)
                else:
                    geom_type = geom.geom_type
                    geom_geojson = mapping(geom)
                    meas_detail, proj_crs = MeasurementService.calculate_measurement(geom, crs_str)

                # Track breakdown
                type_breakdown[geom_type] = type_breakdown.get(geom_type, 0) + 1

                # Track totals
                if meas_detail.type == MeasurementType.AREA and meas_detail.value is not None:
                    total_area += meas_detail.value
                    measured_count += 1
                elif meas_detail.type == MeasurementType.LENGTH and meas_detail.value is not None:
                    total_length += meas_detail.value
                    measured_count += 1

                # Extract attributes
                props = {col: sanitize_value(row[col]) for col in prop_cols}

                features.append(
                    FeatureMeasurement(
                        feature_id=int(idx) if isinstance(idx, (int, np.integer)) else str(idx),
                        geometry_type=geom_type,
                        crs=crs_str,
                        projected_crs=proj_crs,
                        properties=props,
                        geometry=geom_geojson,
                        measurement=meas_detail,
                    )
                )

            summary = MeasurementSummary(
                total_area_sq_m=round(total_area, 2),
                total_length_m=round(total_length, 2),
                geometry_types_breakdown=type_breakdown,
                total_features_measured=measured_count,
            )

            return crs_str, len(features), features, summary

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _process_kml(
        cls, kml_path: Path
    ) -> Tuple[str, int, List[FeatureMeasurement], MeasurementSummary]:
        """
        Parses KML file (which defaults to EPSG:4326), extracting Placemark geometries and attributes.
        Uses GeoPandas / Fiona with fallback to fastkml / XML parsing for maximum robustness.
        """
        crs_str = "EPSG:4326"

        try:
            # Try reading with GeoPandas / Fiona first
            gdf = gpd.read_file(kml_path, driver="KML")
            if gdf.crs:
                crs_str = CRSTransformer.normalize_crs(gdf.crs)

            features: List[FeatureMeasurement] = []
            total_area = 0.0
            total_length = 0.0
            type_breakdown: Dict[str, int] = {}
            measured_count = 0

            prop_cols = [col for col in gdf.columns if col != gdf.geometry.name]

            for idx, row in gdf.iterrows():
                geom: Optional[BaseGeometry] = row.get(gdf.geometry.name)
                if geom is None or geom.is_empty:
                    geom_type = "None"
                    geom_geojson = None
                    meas_detail, proj_crs = MeasurementService.calculate_measurement(None, crs_str)
                else:
                    geom_type = geom.geom_type
                    geom_geojson = mapping(geom)
                    meas_detail, proj_crs = MeasurementService.calculate_measurement(geom, crs_str)

                type_breakdown[geom_type] = type_breakdown.get(geom_type, 0) + 1

                if meas_detail.type == MeasurementType.AREA and meas_detail.value is not None:
                    total_area += meas_detail.value
                    measured_count += 1
                elif meas_detail.type == MeasurementType.LENGTH and meas_detail.value is not None:
                    total_length += meas_detail.value
                    measured_count += 1

                props = {col: sanitize_value(row[col]) for col in prop_cols}

                features.append(
                    FeatureMeasurement(
                        feature_id=int(idx) if isinstance(idx, (int, np.integer)) else str(idx),
                        geometry_type=geom_type,
                        crs=crs_str,
                        projected_crs=proj_crs,
                        properties=props,
                        geometry=geom_geojson,
                        measurement=meas_detail,
                    )
                )

            summary = MeasurementSummary(
                total_area_sq_m=round(total_area, 2),
                total_length_m=round(total_length, 2),
                geometry_types_breakdown=type_breakdown,
                total_features_measured=measured_count,
            )
            return crs_str, len(features), features, summary

        except Exception:
            # Fallback to direct FastKML / XML Placemark extraction
            return cls._fallback_parse_kml(kml_path)

    @classmethod
    def _fallback_parse_kml(
        cls, kml_path: Path
    ) -> Tuple[str, int, List[FeatureMeasurement], MeasurementSummary]:
        """
        Fallback parser using FastKML / PyGeoIf / Shapely.
        """
        crs_str = "EPSG:4326"
        features: List[FeatureMeasurement] = []
        total_area = 0.0
        total_length = 0.0
        type_breakdown: Dict[str, int] = {}
        measured_count = 0

        with open(kml_path, "rb") as f:
            raw_bytes = f.read()

        try:
            k = kml.KML()
            k.from_string(raw_bytes)

            placemarks = []

            def extract_placemarks(element):
                if hasattr(element, "features"):
                    for feat in element.features:
                        extract_placemarks(feat)
                if isinstance(element, kml.Placemark) or getattr(element, "geometry", None) is not None:
                    placemarks.append(element)

            for feat in k.features:
                extract_placemarks(feat)

            for idx, pm in enumerate(placemarks):
                geom_obj = getattr(pm, "geometry", None)
                if geom_obj is None:
                    continue

                # Convert pygeoif / fastkml geometry to shapely
                if hasattr(geom_obj, "__geo_interface__"):
                    geom = shape(geom_obj.__geo_interface__)
                else:
                    geom = shape(geom_obj)

                geom_type = geom.geom_type
                geom_geojson = mapping(geom)
                meas_detail, proj_crs = MeasurementService.calculate_measurement(geom, crs_str)

                type_breakdown[geom_type] = type_breakdown.get(geom_type, 0) + 1

                if meas_detail.type == MeasurementType.AREA and meas_detail.value is not None:
                    total_area += meas_detail.value
                    measured_count += 1
                elif meas_detail.type == MeasurementType.LENGTH and meas_detail.value is not None:
                    total_length += meas_detail.value
                    measured_count += 1

                props = {
                    "name": getattr(pm, "name", None) or f"Feature_{idx}",
                    "description": getattr(pm, "description", None) or "",
                }

                features.append(
                    FeatureMeasurement(
                        feature_id=idx,
                        geometry_type=geom_type,
                        crs=crs_str,
                        projected_crs=proj_crs,
                        properties=props,
                        geometry=geom_geojson,
                        measurement=meas_detail,
                    )
                )

        except Exception as e:
            # If fastkml also fails, let's try pure XML coordinate parser as ultimate fallback
            return cls._parse_kml_xml_pure(raw_bytes)

        summary = MeasurementSummary(
            total_area_sq_m=round(total_area, 2),
            total_length_m=round(total_length, 2),
            geometry_types_breakdown=type_breakdown,
            total_features_measured=measured_count,
        )

        return crs_str, len(features), features, summary

    @classmethod
    def _parse_kml_xml_pure(
        cls, raw_bytes: bytes
    ) -> Tuple[str, int, List[FeatureMeasurement], MeasurementSummary]:
        """
        Pure XML fallback parser for KML Placemarks (Polygon, LineString, Point).
        """
        crs_str = "EPSG:4326"
        features: List[FeatureMeasurement] = []
        total_area = 0.0
        total_length = 0.0
        type_breakdown: Dict[str, int] = {}
        measured_count = 0

        root = ET.fromstring(raw_bytes)
        # Namespace strip
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        placemarks = root.findall(".//Placemark")
        from shapely.geometry import Polygon as ShapelyPolygon, LineString as ShapelyLineString, Point as ShapelyPoint

        for idx, pm in enumerate(placemarks):
            name_el = pm.find("name")
            name = name_el.text.strip() if name_el is not None and name_el.text else f"Feature_{idx}"
            desc_el = pm.find("description")
            description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

            geom = None
            poly = pm.find(".//Polygon")
            if poly is not None:
                coords_el = poly.find(".//coordinates")
                if coords_el is not None and coords_el.text:
                    pts = []
                    for token in coords_el.text.strip().split():
                        parts = [float(p) for p in token.split(",") if p.strip()]
                        if len(parts) >= 2:
                            pts.append((parts[0], parts[1]))
                    if len(pts) >= 3:
                        geom = ShapelyPolygon(pts)

            if geom is None:
                line = pm.find(".//LineString")
                if line is not None:
                    coords_el = line.find(".//coordinates")
                    if coords_el is not None and coords_el.text:
                        pts = []
                        for token in coords_el.text.strip().split():
                            parts = [float(p) for p in token.split(",") if p.strip()]
                            if len(parts) >= 2:
                                pts.append((parts[0], parts[1]))
                        if len(pts) >= 2:
                            geom = ShapelyLineString(pts)

            if geom is None:
                pt = pm.find(".//Point")
                if pt is not None:
                    coords_el = pt.find(".//coordinates")
                    if coords_el is not None and coords_el.text:
                        parts = [float(p) for p in coords_el.text.strip().split(",") if p.strip()]
                        if len(parts) >= 2:
                            geom = ShapelyPoint(parts[0], parts[1])

            if geom is None:
                continue

            geom_type = geom.geom_type
            geom_geojson = mapping(geom)
            meas_detail, proj_crs = MeasurementService.calculate_measurement(geom, crs_str)

            type_breakdown[geom_type] = type_breakdown.get(geom_type, 0) + 1

            if meas_detail.type == MeasurementType.AREA and meas_detail.value is not None:
                total_area += meas_detail.value
                measured_count += 1
            elif meas_detail.type == MeasurementType.LENGTH and meas_detail.value is not None:
                total_length += meas_detail.value
                measured_count += 1

            props = {"name": name, "description": description}

            features.append(
                FeatureMeasurement(
                    feature_id=idx,
                    geometry_type=geom_type,
                    crs=crs_str,
                    projected_crs=proj_crs,
                    properties=props,
                    geometry=geom_geojson,
                    measurement=meas_detail,
                )
            )

        summary = MeasurementSummary(
            total_area_sq_m=round(total_area, 2),
            total_length_m=round(total_length, 2),
            geometry_types_breakdown=type_breakdown,
            total_features_measured=measured_count,
        )

        return crs_str, len(features), features, summary
