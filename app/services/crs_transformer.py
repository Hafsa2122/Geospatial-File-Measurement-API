import math
from typing import Optional, Tuple
import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


class CRSTransformer:
    """
    Handles coordinate reference system detection, validation, and projection.
    Ensures that geographic coordinates (degrees) are accurately projected into metric
    coordinate systems (such as UTM) before measuring area or length.
    """

    @staticmethod
    def normalize_crs(crs_input: Optional[any]) -> str:
        """
        Normalizes various CRS representations into a standard EPSG string or WKT string.
        Defaults to EPSG:4326 if not specified or unrecognized.
        """
        if crs_input is None:
            return "EPSG:4326"
        
        try:
            crs_obj = pyproj.CRS.from_user_input(crs_input)
            auth = crs_obj.to_authority()
            if auth:
                return f"{auth[0]}:{auth[1]}"
            epsg = crs_obj.to_epsg()
            if epsg:
                return f"EPSG:{epsg}"
            return crs_obj.to_string()
        except Exception:
            # Fallback to string representation or EPSG:4326
            crs_str = str(crs_input).strip()
            if crs_str.upper().startswith("EPSG:"):
                return crs_str.upper()
            return "EPSG:4326"

    @staticmethod
    def is_projected(crs_name: str) -> bool:
        """
        Checks if the provided CRS is a projected coordinate system (units in meters).
        """
        try:
            crs_obj = pyproj.CRS.from_user_input(crs_name)
            return crs_obj.is_projected
        except Exception:
            return False

    @classmethod
    def get_optimal_utm_crs(cls, lon: float, lat: float) -> str:
        """
        Calculates the optimal UTM (Universal Transverse Mercator) projected EPSG code
        for a given longitude and latitude centroid.
        
        - Northern Hemisphere: EPSG:32601 to EPSG:32660
        - Southern Hemisphere: EPSG:32701 to EPSG:32760
        - Polar Regions: UPS North (EPSG:32661) / UPS South (EPSG:32761)
        """
        # Handle polar extremes
        if lat > 84.0:
            return "EPSG:32661"  # UPS North
        if lat < -80.0:
            return "EPSG:32761"  # UPS South

        # Ensure longitude is in [-180, 180]
        norm_lon = (lon + 180) % 360 - 180
        zone_num = int(math.floor((norm_lon + 180) / 6)) + 1
        zone_num = max(1, min(60, zone_num))

        if lat >= 0:
            return f"EPSG:{32600 + zone_num}"
        else:
            return f"EPSG:{32700 + zone_num}"

    @classmethod
    def transform_to_projected(
        cls, geometry: BaseGeometry, source_crs: str
    ) -> Tuple[BaseGeometry, str]:
        """
        Transforms a Shapely geometry from its source CRS into an appropriate projected
        metric CRS (e.g. UTM zone), returning the projected geometry and target CRS code.
        """
        if geometry.is_empty:
            return geometry, source_crs

        norm_source = cls.normalize_crs(source_crs)
        source_obj = pyproj.CRS.from_user_input(norm_source)

        # If already projected with metric units, return as-is
        if source_obj.is_projected:
            return geometry, norm_source

        # Source is geographic (degrees), find centroid in lon/lat
        centroid = geometry.centroid
        lon, lat = centroid.x, centroid.y

        # Determine target projected CRS (UTM Zone)
        target_crs_str = cls.get_optimal_utm_crs(lon, lat)
        target_obj = pyproj.CRS.from_user_input(target_crs_str)

        # Create transformer (always_xy=True ensures (x, y) / (lon, lat) order)
        project = pyproj.Transformer.from_crs(source_obj, target_obj, always_xy=True).transform
        projected_geometry = transform(project, geometry)

        return projected_geometry, target_crs_str
