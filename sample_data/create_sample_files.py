import os
import zipfile
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point

OUTPUT_DIR = Path(__file__).parent
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_kml_files():
    # 1. Sample Polygon KML (approx ~4.1 sq km Central Park representation)
    polygon_kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Sample Central Park Area</name>
    <description>Agricultural and Park Boundary Sample</description>
    <Placemark>
      <name>Central Park Reservoir Perimeter</name>
      <description>Reservoir enclosure</description>
      <Polygon>
        <extrude>1</extrude>
        <altitudeMode>relativeToGround</altitudeMode>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -73.9620,40.7850,0
              -73.9570,40.7850,0
              -73.9570,40.7810,0
              -73.9620,40.7810,0
              -73.9620,40.7850,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    (OUTPUT_DIR / "sample_polygon.kml").write_text(polygon_kml, encoding="utf-8")

    # 2. Sample LineString KML
    linestring_kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Sample River Route</name>
    <description>LineString trail example</description>
    <Placemark>
      <name>Hudson River Segment</name>
      <description>River walking route</description>
      <LineString>
        <coordinates>
          -73.9850,40.7480,0
          -73.9800,40.7520,0
          -73.9750,40.7580,0
          -73.9700,40.7620,0
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
"""
    (OUTPUT_DIR / "sample_linestring.kml").write_text(linestring_kml, encoding="utf-8")

    # 3. Sample Points KML
    points_kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Landmarks</name>
    <Placemark>
      <name>Empire State Building</name>
      <Point>
        <coordinates>-73.9857,40.7484,0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Times Square</name>
      <Point>
        <coordinates>-73.9851,40.7580,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
"""
    (OUTPUT_DIR / "sample_points.kml").write_text(points_kml, encoding="utf-8")

    # 4. Mixed Features KML
    mixed_kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Survey Area Complete</name>
    <Placemark>
      <name>Field Zone A</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -73.960,40.780,0
              -73.950,40.780,0
              -73.950,40.770,0
              -73.960,40.770,0
              -73.960,40.780,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>Irrigation Pipeline</name>
      <LineString>
        <coordinates>
          -73.960,40.780,0
          -73.955,40.775,0
          -73.950,40.770,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Weather Sensor Station</name>
      <Point>
        <coordinates>-73.955,40.775,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
"""
    (OUTPUT_DIR / "sample_survey_mixed.kml").write_text(mixed_kml, encoding="utf-8")
    print("Created KML sample files.")


def create_shapefile_zip():
    # Create GeoDataFrame with Polygon, LineString, and Point features
    polys = [
        Polygon([(-73.960, 40.780), (-73.950, 40.780), (-73.950, 40.770), (-73.960, 40.770), (-73.960, 40.780)]),
        Polygon([(-73.940, 40.760), (-73.930, 40.760), (-73.930, 40.750), (-73.940, 40.750), (-73.940, 40.760)]),
    ]
    
    gdf = gpd.GeoDataFrame(
        {
            "plot_id": ["PLOT_001", "PLOT_002"],
            "zone_type": ["Agricultural", "Commercial"],
            "owner": ["Acme Corp", "GreenFields LLC"],
            "geometry": polys,
        },
        crs="EPSG:4326"
    )

    temp_shp_dir = OUTPUT_DIR / "temp_shp"
    temp_shp_dir.mkdir(parents=True, exist_ok=True)
    shp_base = temp_shp_dir / "plots.shp"
    
    gdf.to_file(shp_base, driver="ESRI Shapefile")

    # Zip all generated files (.shp, .shx, .dbf, .prj, .cpg)
    zip_path = OUTPUT_DIR / "sample_shapefile.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in temp_shp_dir.glob("plots.*"):
            zf.write(file, arcname=file.name)

    # Cleanup temp dir
    import shutil
    shutil.rmtree(temp_shp_dir, ignore_errors=True)
    print("Created Shapefile ZIP sample.")


if __name__ == "__main__":
    create_kml_files()
    create_shapefile_zip()
