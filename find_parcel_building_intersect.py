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
intersectOutput = "building_flooding_zone_intersect_output"

# Check if the feature class exists
if not arcpy.Exists(intersectOutput):
    # If not, create it
    arcpy.CreateFeatureclass_management(
        arcpy.env.workspace, intersectOutput, "POLYGON")

# Spatial join parcels and buildings to assign parcel's gml_id and uid to buildings
arcpy.analysis.SpatialJoin(
    "selected_buildings2", "record_parcel_check", "building_within_parcel_joined",
    join_operation='JOIN_ONE_TO_ONE', join_type='KEEP_COMMON', field_mapping=None,
    match_option='INTERSECT', search_radius=None, distance_field_name=None)

# Get all the unique building IDs (now with gml_id and uid) from the joined building layer
building_ids_and_uids = [(row[0], row[1], row[2]) for row in arcpy.da.SearchCursor(
    "building_within_parcel_joined", ["gml_id", "uid", "objectid"])]

arcpy.AddMessage(f"building_ids_and_uids : {building_ids_and_uids}")


# Define the periods and types
periods = ["1: 50 year", "1: 100 year", "1: 500 year"]
types = ["surface_water", "river"]

merged_results = []

# Loop through each unique building ID
parcel_processed_array = []
for gml_id, uid, objectid in building_ids_and_uids:

    if gml_id in parcel_processed_array:
        continue

    # Select the building from the joined building layer
    where_clause = f"gml_id = '{gml_id}' AND uid = {uid}"
    arcpy.MakeFeatureLayer_management(
        "building_within_parcel_joined", "selected_building", where_clause)

    # Intersect the selected building with the "selected_flooding_zone_5m_square_grid2" layer
    arcpy.analysis.Intersect(
        ["selected_building", inFeatures[1]], intersectOutput)

    # Calculate the total area of the selected building
    arcpy.AddGeometryAttributes_management("selected_building", "AREA")
    # total_building_area = sum(row[0] for row in arcpy.da.SearchCursor(
    #     "selected_building", 'POLY_AREA'))
    total_building_area = 0
    for row in arcpy.da.SearchCursor("selected_building", ['POLY_AREA', 'objectid']):
        total_building_area = total_building_area + row[0]
        arcpy.AddMessage(f"objectid: {row[1]}, area: {row[0]}")

    parcel_processed_array.append(gml_id)

    arcpy.AddMessage(
        f"Total Building Area for Building ID {objectid}, Parcel ID: {gml_id}: {total_building_area}")

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
                intersectOutput, "selected_building", where_clause)

            # Calculate the total area of the selected intersected polygons
            arcpy.AddGeometryAttributes_management("selected_building", "AREA")

            # Initialize variable to keep track of the total intersect area for the current type and period
            total_intersect_area = 0
            max_depth = 0
            record_count = 0

            # Loop through each polygon in the selected set
            for row in arcpy.da.SearchCursor("selected_building", ['POLY_AREA', 'depth']):
                # Update the total intersect area
                total_intersect_area += row[0]
                if max_depth < row[1]:
                    max_depth = row[1]
                record_count = record_count + 1

            percentage = (total_intersect_area / total_building_area) * \
                100 if total_building_area else 0

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
tableRiskExposure = 'RiskExposureInBuilding'
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
