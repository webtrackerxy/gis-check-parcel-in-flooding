import arcpy
from arcpy import env

# Set workspace
# workspace = "C:\\working\gb\\Flooding\\test\\store.gdb"
# env.workspace = workspace

# Get the current project
aprx = arcpy.mp.ArcGISProject('CURRENT')
# Set the workspace to the current project's default geodatabase
arcpy.env.workspace = aprx.defaultGeodatabase
workspace = arcpy.env.workspace

# Set local variables
inFeatures = ["record_parcel_check", "selected_flooding_zone_5m_square_grid2"]
intersectOutput = "parcel_flooding_zone_intersect_output"

# Check if the feature class exists
if not arcpy.Exists(intersectOutput):
    # If not, create it
    arcpy.CreateFeatureclass_management(
        arcpy.env.workspace, intersectOutput, "POLYGON")

# Collect all Intersect areas
arcpy.analysis.Intersect(
    inFeatures, "parcel_flooding_zone_intersect_output_preview")

# Add a new field to hold the calculation
arcpy.management.AddField(intersectOutput, "percentage", "DOUBLE")

# Define the periods and types
periods = ["1: 50 year", "1: 100 year", "1: 500 year"]
types = ["surface_water", "river"]

# Get all the unique parcel IDs from the "record_parcel_check" layer
parcel_ids_and_uids = [(row[0], row[1]) for row in arcpy.da.SearchCursor(
    inFeatures[0], ["gml_id", "uid"])]


arcpy.AddMessage(f"parcel_ids : {parcel_ids_and_uids}")

merged_results = []

# Loop through each unique parcel ID
for gml_id, uid in parcel_ids_and_uids:    # Select the parcel from the "record_parcel_check" layer

    where_clause = f"gml_id = '{gml_id}' AND uid = {uid}"
    # arcpy.AddMessage(f"where_clause: {where_clause}")
    arcpy.MakeFeatureLayer_management(
        inFeatures[0], "selected_parcel", where_clause)

    # Intersect the selected parcel with the "selected_flooding_zone_5m_square_grid2" layer
    arcpy.analysis.Intersect(
        ["selected_parcel", inFeatures[1]], intersectOutput)

    # Calculate the total area of the selected parcel
    arcpy.AddGeometryAttributes_management("selected_parcel", "AREA")
    total_parcel_area = sum(row[0] for row in arcpy.da.SearchCursor(
        "selected_parcel", 'POLY_AREA'))
    arcpy.AddMessage(
        f"Total Parcel Area for Parcel ID {gml_id} : {total_parcel_area}")

    # Dictionaries to store percentage values and max depths
    percentage_dict = {}
    max_depth_dict = {}
    # Calculate the percentage of overlay and max depth for each combination of period and type
    for period in periods:
        for type in types:
            # Create the where clause
            where_clause = f"return_periods = '{period}' AND type = '{type}'"

            # Create a feature layer with the desired selection
            arcpy.MakeFeatureLayer_management(
                intersectOutput, "selected_polygons", where_clause)

            # Calculate the total area of the selected intersected polygons
            arcpy.AddGeometryAttributes_management("selected_polygons", "AREA")

            # Initialize variable to keep track of the total intersect area for the current type and period
            total_intersect_area = 0
            max_depth = 0
            record_count = 0

            # Loop through each polygon in the selected set
            for row in arcpy.da.SearchCursor("selected_polygons", ['POLY_AREA', 'depth']):
                # Update the total intersect area
                total_intersect_area += row[0]
                if max_depth < row[1]:
                    max_depth = row[1]
                record_count = record_count + 1

            percentage = (total_intersect_area / total_parcel_area) * \
                100 if total_parcel_area else 0

            # Define the key for each combination of period and type
            period_number = period.split(" ")[1]
            type_key = type.title().replace("_", "")
            exposure_key = f'FloodExposure{period_number}Years{type_key}'
            depth_key = f'FloodMaxDepth{period_number}Years{type_key}'

            # Store the calculated data in the corresponding dictionaries
            percentage_dict[exposure_key] = percentage
            max_depth_dict[depth_key] = max_depth
            merged_percentage_depth = percentage_dict | max_depth_dict

            arcpy.AddMessage(
                f"For type: {type}, period: {period}, total_intersect_area, {total_intersect_area}, count: {record_count}, the percentage of overlay is: {percentage}, max depth: {max_depth}")

    merged_results.append({"RecordID": uid,
                           "ParcelID": gml_id} | merged_percentage_depth)

arcpy.AddMessage(
    f"results : {merged_results}")

# Create the new table

tableRiskExposure = 'RiskExposureInParcel'
if not arcpy.Exists(tableRiskExposure):
    arcpy.CreateTable_management(workspace, tableRiskExposure)

    fields_and_types = [
        ("RecordID", "TEXT"),
        ("ParcelID", "TEXT"),
        ("FloodExposure50YearsRiver", "DOUBLE"),
        ("FloodExposure100YearsRiver", "DOUBLE"),
        ("FloodExposure500YearsRiver", "DOUBLE"),
        ("FloodExposure50YearsSurfaceWater", "DOUBLE"),
        ("FloodExposure100YearsSurfaceWater", "DOUBLE"),
        ("FloodExposure500YearsSurfaceWater", "DOUBLE"),
        ("FloodMaxDepth50YearsRiver", "DOUBLE"),
        ("FloodMaxDepth100YearsRiver", "DOUBLE"),
        ("FloodMaxDepth500YearsRiver", "DOUBLE"),
        ("FloodMaxDepth50YearsSurfaceWater", "DOUBLE"),
        ("FloodMaxDepth100YearsSurfaceWater", "DOUBLE"),
        ("FloodMaxDepth500YearsSurfaceWater", "DOUBLE")
    ]

    for field_name, field_type in fields_and_types:
        arcpy.AddField_management(tableRiskExposure, field_name, field_type)

# Delete all data
arcpy.DeleteRows_management(tableRiskExposure)

fields = ["RecordID", "ParcelID",
          "FloodExposure50YearsRiver", "FloodExposure100YearsRiver", "FloodExposure500YearsRiver",
          "FloodExposure50YearsSurfaceWater", "FloodExposure100YearsSurfaceWater", "FloodExposure500YearsSurfaceWater",
          "FloodMaxDepth50YearsRiver", "FloodMaxDepth100YearsRiver", "FloodMaxDepth500YearsRiver",
          "FloodMaxDepth50YearsSurfaceWater", "FloodMaxDepth100YearsSurfaceWater", "FloodMaxDepth500YearsSurfaceWater"]

for result in merged_results:
    # Open a new cursor for inserting data
    with arcpy.da.InsertCursor(tableRiskExposure, fields) as cursor:
        # Prepare the row to insert
        row = [result.get(field, None) for field in fields]

        # Insert the row
        cursor.insertRow(row)
