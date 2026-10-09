from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MeasurementType(str, Enum):
    AREA = "area"
    LENGTH = "length"
    NONE = "none"
    UNSUPPORTED = "unsupported"


class MeasurementDetail(BaseModel):
    type: MeasurementType = Field(..., description="Type of measurement calculated: area, length, none, unsupported")
    value: Optional[float] = Field(None, description="Primary numerical value in standard SI units (m² for area, m for length)")
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g., 'square_meters', 'meters')")
    formatted: Optional[str] = Field(None, description="Human-readable formatted string (e.g., '15,420.55 m²')")
    conversions: Optional[Dict[str, float]] = Field(default_factory=dict, description="Alternative units (e.g., hectares, square_km, km, feet)")
    note: Optional[str] = Field(None, description="Informative note or reason if not measured")


class FeatureMeasurement(BaseModel):
    feature_id: Union[int, str] = Field(..., description="Unique index or ID of the feature within the file")
    geometry_type: str = Field(..., description="Geospatial geometry type (e.g., Polygon, LineString, Point)")
    crs: str = Field(..., description="Original coordinate reference system (e.g., EPSG:4326)")
    projected_crs: Optional[str] = Field(None, description="Projected CRS used for accurate metric calculation")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Feature attributes extracted from source file")
    geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON geometry representation")
    measurement: MeasurementDetail = Field(..., description="Measurement details for this feature")


class MeasurementSummary(BaseModel):
    total_area_sq_m: float = Field(0.0, description="Sum of all polygon areas in square meters")
    total_length_m: float = Field(0.0, description="Sum of all linestring lengths in meters")
    geometry_types_breakdown: Dict[str, int] = Field(default_factory=dict, description="Count of each geometry type")
    total_features_measured: int = Field(0, description="Number of features with calculated measurements")


class FileInfoResponse(BaseModel):
    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename of the uploaded file")
    feature_count: int = Field(..., description="Total number of features in the file")
    crs: str = Field(..., description="Coordinate Reference System identified")
    status: ProcessingStatus = Field(..., description="Processing status")
    created_at: Optional[datetime] = Field(None, description="Upload timestamp")
    error_message: Optional[str] = Field(None, description="Error details if processing failed")


class FileMeasurementResponse(BaseModel):
    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    feature_count: int = Field(..., description="Total number of features")
    crs: str = Field(..., description="Original Coordinate Reference System")
    status: ProcessingStatus = Field(..., description="Processing status")
    features: List[FeatureMeasurement] = Field(..., description="List of processed features with individual measurements")
    summary: MeasurementSummary = Field(..., description="Aggregated measurement summary")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Detailed description of the error")
    code: Optional[str] = Field(None, description="Error code identifier")
