from typing import Optional, Tuple
from shapely.geometry.base import BaseGeometry
from shapely.geometry import (
    Polygon, MultiPolygon,
    LineString, MultiLineString,
    Point, MultiPoint,
    GeometryCollection
)
from app.models.schemas import MeasurementDetail, MeasurementType
from app.services.crs_transformer import CRSTransformer


class MeasurementService:
    """
    Computes geometric measurements (Area, Length) on transformed metric geometries.
    Handles supported and unsupported geometry types gracefully without crashing.
    """

    @classmethod
    def calculate_measurement(
        cls, geometry: BaseGeometry, source_crs: str
    ) -> Tuple[MeasurementDetail, Optional[str]]:
        """
        Calculates measurement for a geometry based on its type.
        Returns the MeasurementDetail model and the projected CRS used.
        """
        if geometry is None or geometry.is_empty:
            return (
                MeasurementDetail(
                    type=MeasurementType.NONE,
                    value=None,
                    unit=None,
                    formatted=None,
                    note="Empty or null geometry provided",
                ),
                None,
            )

        geom_type = geometry.geom_type

        # 1. Polygon / MultiPolygon -> Area Measurement
        if isinstance(geometry, (Polygon, MultiPolygon)) or geom_type in ("Polygon", "MultiPolygon"):
            try:
                proj_geom, proj_crs = CRSTransformer.transform_to_projected(geometry, source_crs)
                area_sq_m = float(proj_geom.area)
                
                # Conversions
                hectares = round(area_sq_m / 10_000.0, 4)
                sq_km = round(area_sq_m / 1_000_000.0, 6)
                acres = round(area_sq_m * 0.000247105, 4)

                return (
                    MeasurementDetail(
                        type=MeasurementType.AREA,
                        value=round(area_sq_m, 2),
                        unit="square_meters",
                        formatted=f"{area_sq_m:,.2f} m²",
                        conversions={
                            "hectares": hectares,
                            "square_kilometers": sq_km,
                            "acres": acres,
                        },
                        note=f"Calculated in projected metric CRS: {proj_crs}",
                    ),
                    proj_crs,
                )
            except Exception as e:
                return (
                    MeasurementDetail(
                        type=MeasurementType.UNSUPPORTED,
                        value=None,
                        unit=None,
                        formatted=None,
                        note=f"Failed to calculate area: {str(e)}",
                    ),
                    None,
                )

        # 2. LineString / MultiLineString -> Length Measurement
        elif isinstance(geometry, (LineString, MultiLineString)) or geom_type in ("LineString", "MultiLineString"):
            try:
                proj_geom, proj_crs = CRSTransformer.transform_to_projected(geometry, source_crs)
                length_m = float(proj_geom.length)

                # Conversions
                km = round(length_m / 1000.0, 4)
                miles = round(length_m * 0.000621371, 4)
                feet = round(length_m * 3.28084, 2)

                return (
                    MeasurementDetail(
                        type=MeasurementType.LENGTH,
                        value=round(length_m, 2),
                        unit="meters",
                        formatted=f"{length_m:,.2f} m",
                        conversions={
                            "kilometers": km,
                            "miles": miles,
                            "feet": feet,
                        },
                        note=f"Calculated in projected metric CRS: {proj_crs}",
                    ),
                    proj_crs,
                )
            except Exception as e:
                return (
                    MeasurementDetail(
                        type=MeasurementType.UNSUPPORTED,
                        value=None,
                        unit=None,
                        formatted=None,
                        note=f"Failed to calculate length: {str(e)}",
                    ),
                    None,
                )

        # 3. Point / MultiPoint -> No measurement required
        elif isinstance(geometry, (Point, MultiPoint)) or geom_type in ("Point", "MultiPoint"):
            return (
                MeasurementDetail(
                    type=MeasurementType.NONE,
                    value=None,
                    unit=None,
                    formatted=None,
                    note="Point geometries have zero dimension; no area or length measurement applicable.",
                ),
                None,
            )

        # 4. Fallback for GeometryCollection or other unhandled geometry types
        else:
            return (
                MeasurementDetail(
                    type=MeasurementType.UNSUPPORTED,
                    value=None,
                    unit=None,
                    formatted=None,
                    note=f"Geometry type '{geom_type}' is not supported for single-metric measurement.",
                ),
                None,
            )
