import threading
from typing import Dict, Optional, List
from datetime import datetime, timezone
from app.models.schemas import (
    FileInfoResponse,
    FileMeasurementResponse,
    ProcessingStatus,
    FeatureMeasurement,
    MeasurementSummary,
)


class FileStorageRepository:
    """
    Thread-safe repository for storing uploaded geospatial files and their computed measurements.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._file_records: Dict[str, FileInfoResponse] = {}
        self._measurement_records: Dict[str, FileMeasurementResponse] = {}

    def save_file(
        self,
        file_id: str,
        filename: str,
        crs: str,
        feature_count: int,
        status: ProcessingStatus,
        features: List[FeatureMeasurement],
        summary: MeasurementSummary,
        error_message: Optional[str] = None,
    ) -> FileInfoResponse:
        with self._lock:
            file_info = FileInfoResponse(
                id=file_id,
                filename=filename,
                feature_count=feature_count,
                crs=crs,
                status=status,
                created_at=datetime.now(timezone.utc),
                error_message=error_message,
            )
            self._file_records[file_id] = file_info

            measurement_info = FileMeasurementResponse(
                id=file_id,
                filename=filename,
                feature_count=feature_count,
                crs=crs,
                status=status,
                features=features,
                summary=summary,
            )
            self._measurement_records[file_id] = measurement_info
            return file_info

    def get_file_info(self, file_id: str) -> Optional[FileInfoResponse]:
        with self._lock:
            return self._file_records.get(file_id)

    def get_file_measurements(self, file_id: str) -> Optional[FileMeasurementResponse]:
        with self._lock:
            return self._measurement_records.get(file_id)

    def list_all_files(self) -> List[FileInfoResponse]:
        with self._lock:
            return list(self._file_records.values())

    def delete_file(self, file_id: str) -> bool:
        with self._lock:
            removed_info = self._file_records.pop(file_id, None)
            self._measurement_records.pop(file_id, None)
            return removed_info is not None

    def clear(self):
        with self._lock:
            self._file_records.clear()
            self._measurement_records.clear()


# Global singleton repository instance
storage_repo = FileStorageRepository()
