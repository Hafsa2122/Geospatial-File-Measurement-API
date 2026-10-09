from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import files_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="""
# 🌍 Geospatial File Measurement API

A production-grade microservice for processing geospatial files (**Shapefiles .zip** and **KML**), transforming coordinates from geographic CRS to optimal projected metric coordinate systems (UTM), and calculating accurate geometric measurements (Area for Polygons, Length for LineStrings).

## Key Features
- 📁 **File Support**: Processes `.kml` files and `.zip` archives containing ESRI Shapefiles.
- 📐 **Accurate Measurements**: Computes metric areas ($m^2$, hectares, $km^2$) and lengths ($m$, $km$, miles) without geodesic coordinate distortion.
- 🌐 **Dynamic CRS Handling**: Detects input CRS (e.g. `EPSG:4326`) and transforms geometries to optimal local UTM projection zones.
- 🛡️ **Fault Tolerant**: Gracefully handles mixed geometry types, points, empty geometries, and unsupported shapes without crashing.
- ⚡ **Interactive Documentation**: OpenAPI/Swagger UI and ReDoc out-of-the-box.
""",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(files_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["Health & Status"])
async def root():
    """
    Health check and basic API information.
    """
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "healthy",
        "documentation": "/docs",
        "endpoints": {
            "upload_file": "POST /api/files/",
            "list_files": "GET /api/files/",
            "get_file_info": "GET /api/files/{id}/",
            "get_measurements": "GET /api/files/{id}/measurements/",
            "delete_file": "DELETE /api/files/{id}/",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
