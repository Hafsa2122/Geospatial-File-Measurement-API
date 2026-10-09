import uuid
import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import (
    FileInfoResponse,
    FileMeasurementResponse,
    ProcessingStatus,
    ErrorResponse,
)
from app.services.file_processor import FileProcessorService
from app.storage.db import storage_repo

router = APIRouter(prefix="/files", tags=["Geospatial Files"])


@router.post(
    "/",
    response_model=FileInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a geospatial file",
    description="Accepts a `.zip` archive containing a Shapefile (.shp, .shx, .dbf) or a `.kml` file. Extracts features, detects CRS, projects geometries to metric systems, and calculates measurements.",
    responses={
        201: {"model": FileInfoResponse, "description": "File successfully uploaded and processed"},
        400: {"model": ErrorResponse, "description": "Invalid file format, corrupted archive, or empty file"},
        500: {"model": ErrorResponse, "description": "Internal processing error"},
    },
)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename."
        )

    filename = file.filename
    file_ext = Path(filename).suffix.lower()

    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats are: {', '.join(settings.ALLOWED_EXTENSIONS)} (.zip for Shapefiles, .kml)."
        )

    # Generate unique ID
    file_id = str(uuid.uuid4())[:8]
    saved_file_path = settings.UPLOAD_DIR / f"{file_id}_{filename}"

    try:
        # Save file to disk
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if saved_file_path.stat().st_size == 0:
            saved_file_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)."
            )

        # Process the geospatial file
        crs_str, feature_count, features, summary = FileProcessorService.process_file(
            saved_file_path, filename
        )

        # Save to database / in-memory store
        file_info = storage_repo.save_file(
            file_id=file_id,
            filename=filename,
            crs=crs_str,
            feature_count=feature_count,
            status=ProcessingStatus.COMPLETED,
            features=features,
            summary=summary,
        )

        return file_info

    except HTTPException:
        # Re-raise HTTP exceptions
        saved_file_path.unlink(missing_ok=True)
        raise
    except ValueError as ve:
        saved_file_path.unlink(missing_ok=True)
        # Store failed record if needed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error during processing: {str(ve)}"
        )
    except Exception as e:
        saved_file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process geospatial file: {str(e)}"
        )


@router.get(
    "/",
    response_model=List[FileInfoResponse],
    summary="List all uploaded geospatial files",
    description="Returns metadata and processing status for all uploaded geospatial files.",
)
async def list_files():
    return storage_repo.list_all_files()


@router.get(
    "/{id}/",
    response_model=FileInfoResponse,
    summary="Get file information",
    description="Returns high-level metadata (ID, filename, feature count, CRS, status) for a specific uploaded file.",
    responses={
        200: {"model": FileInfoResponse, "description": "File information found"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
)
async def get_file_info(id: str):
    file_info = storage_repo.get_file_info(id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found."
        )
    return file_info


@router.get(
    "/{id}/measurements/",
    response_model=FileMeasurementResponse,
    summary="Get feature measurements for a file",
    description="Returns calculated metric measurements (area in m² for Polygons, length in m for LineStrings, handled points) along with attributes, geometry, and summary statistics.",
    responses={
        200: {"model": FileMeasurementResponse, "description": "Measurements retrieved successfully"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
)
async def get_file_measurements(id: str):
    measurement_info = storage_repo.get_file_measurements(id)
    if not measurement_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found."
        )
    return measurement_info


@router.delete(
    "/{id}/",
    status_code=status.HTTP_200_OK,
    summary="Delete an uploaded file record",
    responses={
        200: {"description": "File successfully deleted"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
)
async def delete_file(id: str):
    deleted = storage_repo.delete_file(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found."
        )
    return {"message": f"File '{id}' successfully deleted."}
