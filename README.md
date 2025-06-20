# Proposed Solution to GIS Use Case

**Author**: Mike Li


📄 **To read the full report, please download this PDF:**  
[Solution to GIS use case.pdf](Solution%20to%20GIS%20use%20case.pdf)


## 1. Overview

The solution enhances flood and wildfire risk assessment for large industrial sites. Each record in the client's data only has a single geocoded coordinate. This solution extrapolates flood and wildfire risk data across the entire site, giving a detailed understanding.

### Workflow Components

- **Flood Risk Processing**: Combines parcel, building, and flood layers.
- **Wildfire Risk Processing**: Same method with wildfire layers.
- **Application**: Cloud-based GIS DB and app layer for real-time risk info.
- **User Access**: Via web or ArcGIS Pro desktop.

### Tables

- `RiskExposureInParcel`
- `RiskExposureInBuilding`

These support extensible workflows (e.g., for seismic risk).

## 2. Data Gathering

### Data Types

- **Client Data**: Points with address & asset values.
- **Parcel Data**: Polygons with property boundaries.
- **Building Data**: Polygons with attributes.
- **Flood Data**: Polygons with 1-in-50, 100, and 500 year periods.
- **Wildfire Data**: API-provided hazard levels.

## 3. Risk Assessment

### Steps

- Use buffer + spatial join to map clients to parcels/buildings.
- If no parcel found, use radial search scaled by asset value.
- Repeat for wildfire if building data available.

### Tools

- PostgreSQL + PostGIS
- ArcGIS Pro + Toolbox
- ArcPy (Python)
- Analysis tools: Intersect, Buffer, Spatial Join

### Outputs

- `RiskExposureInParcel`: Exposure & max depth by return period
- `RiskExposureInBuilding`: Same, applied to building footprints

### Simulation

- Provided ArcGIS Pro package shows test data and mock client locations:
  [Download Here](https://drive.google.com/file/d/1Bj1kWwZXSbKFD6Ia3-43R2icX52sx1c3/view)
- Source Code: [GitHub](https://github.com/webtrackerxy/gis-check-parcel-in-flooding)

### Step-by-step Processing

- **Step 1**: Run `1-parcel-check` → Match geocoded points to parcels.
- **Step 2**: Run `2-find-parcel-intersect` → Calculate flood exposure for parcels.
- **Step 3**: Run `3-find-parcel-building-intersect` → Calculate building-level exposure.

## 4. API Development

### Purpose

- Deliver exposure results <1s/location.
- Use ArcGIS Enterprise to deploy a GeoProcessing service.

### Sample ArcPy Script

```python
import psycopg2
import json
import arcpy

conn = psycopg2.connect(dbname="...", user="...", password="...", host="...")
record_id = arcpy.GetParameterAsText(0)

cur = conn.cursor()

sql = f"SELECT ... FROM RiskExposureInParcel ... WHERE recordid = '{record_id}'"
cur.execute(sql)
results = cur.fetchall()

geojson = {"type": "FeatureCollection", "features": [...]}
arcpy.AddMessage(json.dumps(geojson, indent=2))

cur.close()
conn.close()
```

### Optimization

- Use DB indexing.
- Ensure one-to-one joins with client/parcel/building data.

## 5. Data Visualization

Use [ArcGIS Experience Builder](https://www.esri.com/en-us/arcgis/products/arcgis-experience-builder/overview)

### Capabilities

- Visualize maps
- Live GeoJSON layer support
- Edit parcels/radials/buildings
- Widget-based editing tools

### Alternatives (if needed)

- Develop custom web app using ArcGIS API for JavaScript

## 6. Open Source Alternatives

| Tool       | Description                         |
|------------|-------------------------------------|
| QGIS       | Desktop GIS software                |
| GeoServer  | Serve raster/vector via web         |
| PostGIS    | Spatial extension for PostgreSQL    |
| GDAL/OGR   | Read/write geospatial formats       |
| Leaflet    | JS mapping library (web)            |

### Pros

- Free, flexible, standard-compliant

### Cons

- More setup, less support than ESRI stack

---

## References

- 📦 [ArcGIS Project Package](https://drive.google.com/file/d/1Bj1kWwZXSbKFD6Ia3-43R2icX52sx1c3/view)
- 🧠 [GitHub Repository](https://github.com/webtrackerxy/gis-check-parcel-in-flooding)

---
