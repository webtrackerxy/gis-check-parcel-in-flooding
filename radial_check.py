import arcpy
import os

# Define the workspace
# workspace = "C:\\working\gb\\Flooding\\test\\store.gdb"
# arcpy.env.workspace = workspace
# Get the current project
aprx = arcpy.mp.ArcGISProject('CURRENT')
# Set the workspace to the current project's default geodatabase
arcpy.env.workspace = aprx.defaultGeodatabase
workspace = arcpy.env.workspace

# Define input parameters
point_layer = "selected_record_data2"
polygon_layer = "selected_parcel_zone2"

# Create an empty polygon layer for intersected buffers
result = arcpy.CreateFeatureclass_management(
    workspace, 'intersected_buffers', 'POLYGON')
intersected_buffers = result.getOutput(0)

# Add the 'BufferRad' and 'UID' fields to the 'intersected_buffers' layer
arcpy.AddField_management(intersected_buffers, "BufferRad", "DOUBLE")
arcpy.AddField_management(intersected_buffers, "UID", "LONG")
arcpy.AddField_management(intersected_buffers, "NAME", "TEXT")
arcpy.AddField_management(intersected_buffers, "LAT", "FLOAT")
arcpy.AddField_management(intersected_buffers, "LNG", "FLOAT")
arcpy.AddField_management(intersected_buffers, "VALUE", "LONG")

# Initialize an empty list to hold rows to insert
rows_to_insert = []

# Create an UpdateCursor to iterate through each row (point)
with arcpy.da.UpdateCursor(point_layer, ['SHAPE@', 'uid', 'name', 'lat', 'lng', 'value']) as cursor:
    for row in cursor:
        point_geometry = row[0]  # get the point geometry
        buffer_radius = 1  # reset buffer radius for each point
        object_id = row[1]

        buffer_layer = arcpy.Buffer_analysis(
            point_geometry, 'in_memory\\buffer', buffer_radius)

        intersect_count = int(arcpy.GetCount_management(arcpy.Intersect_analysis(
            [buffer_layer, polygon_layer], 'in_memory\\intersect')).getOutput(0))

        if intersect_count == 0:
            buffer_radius = row[5] * 0.3
            buffer_layer = arcpy.Buffer_analysis(
                point_geometry, 'in_memory\\buffer', buffer_radius)
            intersect_count = int(arcpy.GetCount_management(arcpy.Intersect_analysis(
                [buffer_layer, polygon_layer], 'in_memory\\intersect')).getOutput(0))

        if intersect_count > 0:
            singlepart_buffer = arcpy.management.MultipartToSinglepart(
                buffer_layer, 'in_memory\\singlepart_buffer')
            for singlepart in arcpy.da.SearchCursor(singlepart_buffer, 'SHAPE@'):
                # Append a tuple to the list with the buffer's geometry, uid and BufferRad value
                rows_to_insert.append(
                    (singlepart[0], row[1], row[2], row[3], row[4], row[5], buffer_radius))

# Insert the new rows into 'intersected_buffers' outside of the UpdateCursor loop
with arcpy.da.InsertCursor(intersected_buffers, ['SHAPE@', 'uid', 'name', 'lat', 'lng', 'value', 'BufferRad']) as iCursor:
    for row in rows_to_insert:
        iCursor.insertRow(row)

# Perform a spatial join between the polygon_layer and intersected_buffers
arcpy.analysis.SpatialJoin(
    polygon_layer, intersected_buffers, "record_parcel_check")

# Cleanup the 'in_memory' workspace
arcpy.Delete_management("in_memory")
