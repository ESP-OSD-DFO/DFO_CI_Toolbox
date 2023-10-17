# -*- coding: utf-8 -*-

### Toolbox created by Craig Schweitzer and Selina Agbayani ###

import arcpy, os
from arcpy.sa import *


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Data Preparation Toolbox"
        self.alias = "DataPrep"
        self.description = """This toolbox contains a set of tools to support the preparation of 
        spatial data for input into the Cumulative Impact Mapping Toolboxes. The tools can be used
        to manipulate raw input activity data into the format expected by the CE toolboxes. 
        
        The toolbox contains three tools:
            •	Alignment and Projection
            •	Area Weighting
            •	Add Activity Fields
 
        It is important to note that the tools need to be used in order, but not all the tools will be
        needed for all datasets. Data may need to be processed through all steps (1,2,3), only steps 2 
        and 3, or only through step 3, depending on the nature of the data. The input workspaces for the 
        Data Preparation Toolbox should be separate from the input workspaces for the Cumulative Impact 
        Mapping Analysis. The equivalent workspaces in the sample data are in “\CI_DFO_Toolbox\CI_Data_Prep”. 
        Intermediate workspaces should also be distinct from input workspaces to minimize confusion related
        to data versions. When tools are used sequentially, the data for Steps 2 and 3 will be located in the
        workspace geodatabase that is specified in the previous Step."""

        # List of tool classes associated with this toolbox
        self.tools = [Alignment, AreaWeight, AddActivityFields]
        
class Alignment(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Alignment and Projection"
        self.description = """The first step of the data preparation toolbox can be used for an activity 
                            dataset that are not in the same projected coordinate system as the planning unit/
                            reference vector grid (pu_1km), or are vector grids that do not line up with the 
                            reference vector grid (pu_1km). 

                            The tool transforms the data to match the projection and alignment of the reference 
                            vector grid. If the activity feature class is considerably smaller in extent compared 
                            to the reference vector grid, please check the Data Masking checkbox. If selected, the 
                            tool will run the process using the extent of the activity feature class. 

                            Values from the selected fields will be pulled into the centroid of each planning unit 
                            (pu) using extract multi-values to points and copied into the reference vector grid 
                            using spatial join. The output feature class will be a planning unit feature class containing
                            data from the selected fields. 
        
        """
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Output workspace",
            name="outputWorkspace",
            datatype=["DEWorkspace","DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Activity Feature Class",
            name="inFC",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Reference Input Raster",
            name="inRaster",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")
        param2.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\pu_raster_grid_1km')

        param3 = arcpy.Parameter(
            displayName="Name Identifier",
            name="nameVariable",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Output Coordinate System",
            name="outCoordSys",
            datatype="GPSpatialReference",
            parameterType="Required",
            direction="Input")

        param5 = arcpy.Parameter(
            displayName="Is the dataset smaller than the PU raster?",
            name="isMaskNeeded",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        
        param6 = arcpy.Parameter(
            displayName="Target fields to keep",
            name = "keepFields",
            datatype = "GPString",
            parameterType ="Required",
            direction = "Input",
            multiValue="True"
        )        
        
        
                        
        params=[param0, param1, param2, param3, param4, param5, param6]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        
        if not parameters[4].altered:
            inRaster = parameters[2].value
            desc_inRaster = arcpy.Describe(inRaster)
            sr = desc_inRaster.spatialReference
            parameters[4].value = sr
            
        if parameters[1].value:
            keepFields=arcpy.ListFields(parameters[1].valueAsText)
            keepList = []
            for keepField in keepFields:
                keepList.append(keepField.name)
            parameters[6].filter.list=sorted(keepList)
    
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Read in Parameters
        outputWorkspace = parameters[0].valueAsText  # workspace where new layers will be saved
        inFC = parameters[1].value  # data layer that you want to project
        inRaster = parameters[2].valueAsText  # Planning unit raster that you want data to go into
        nameVariable = parameters[3].valueAsText  # name of data being used. i.e. AIS, Invasive Species etc.
        outCoordSys = parameters[4].value  # desired coordinate system for outputs
        isMaskNeeded = parameters[5].value # boolean value for if data is smaller than target raster
        keepFields = parameters[6].valueAsText # intensity attribute fields to be processed

        # set workspace and overwrite
        arcpy.env.workspace = outputWorkspace
        arcpy.AddMessage("The output workspace is " + outputWorkspace)
        arcpy.env.overwriteOutput = True


        # set Environments
        arcpy.env.cellSize = inRaster
        arcpy.env.snapRaster = inRaster
        arcpy.env.extent = inRaster
        arcpy.env.outputCoordinateSystem = outCoordSys

        #assign variable names for point/polygon features generated from reference input raster
        pointsName = nameVariable + "_Grid_Points"
        polygonName = str(inRaster)+"_polygons"
        
        pointsFC = os.path.join(outputWorkspace,pointsName)
        polygonFC = os.path.join(outputWorkspace,polygonName)

        if isMaskNeeded==True:
            # if data is smaller then set environment extent and mask to dataset
            arcpy.env.extent=inFC
            arcpy.env.mask = inFC
            smallRaster=ExtractByMask(inRaster, inFC)
            arcpy.AddMessage("Extent and Mask set to input layer...")
            
            #if exists, overwrite in case different
            if arcpy.Exists(os.path.join(pointsFC)):
                arcpy.management.Delete(pointsFC)
            inPoints = arcpy.RasterToPoint_conversion(smallRaster, pointsFC)
            
            if arcpy.Exists(os.path.join(polygonFC)):
                arcpy.management.Delete(polygonFC)
            inPolygons = arcpy.RasterToPolygon_conversion(smallRaster, polygonFC, "NO_SIMPLIFY")
        else:
            arcpy.AddMessage("Extent and Mask set to the input reference raster...")
            if arcpy.Exists(os.path.join(pointsFC)):
                arcpy.management.Delete(pointsFC)
            inPoints = arcpy.RasterToPoint_conversion(inRaster, pointsFC)
                        
            if arcpy.Exists(os.path.join(polygonFC)):
                arcpy.management.Delete(polygonFC)
            inPolygons = arcpy.RasterToPolygon_conversion(inRaster, polygonFC, "NO_SIMPLIFY")

        arcpy.AddMessage("Points feature class created: " + str(inPoints))

        #if output workspace == feature dataset, move arc.env.workspace up to gdb. 
        desc_outputWorkspace = arcpy.Describe(outputWorkspace)
        if desc_outputWorkspace.dataType == 'FeatureDataset':
            rasterWorkspace = os.path.dirname(outputWorkspace)
            arcpy.env.workspace = rasterWorkspace
            arcpy.AddMessage("Rasters will be saved in "+rasterWorkspace)
        
        
        # create list of fields in input feature layer and create a new raster using value of each field
        fields = arcpy.ListFields(inFC)
        keepField_List = keepFields.split(";")
        
        
        arcpy.AddMessage("Processing fields: "+str(keepField_List))
        for field in fields:
            for keep in keepField_List:
                if keep == field.name:
                    #skip ArcGIS fields
                    if field.type == 'OID' or "OBJECTID" in field.name or field.name.upper() == 'SHAPE_AREA' or field.name.upper() == 'SHAPE_LENGTH':
                        continue
                    elif field.type=="Integer" or field.type=="Double":
                        arcpy.AddMessage("Processing: "+field.name+" ("+field.type+")")
                        rasterName= nameVariable+"_"+str(field.name)
                        arcpy.PolygonToRaster_conversion(inFC, field.name, rasterName)
                        arcpy.AddMessage("Raster created: "+str(rasterName))
                else:
                    continue
                
        arcpy.AddMessage("Shifting input data to match the reference raster grid...")
        
        # generate list of rasters created in above step
        rasterList = arcpy.ListRasters()
        
        #extract all integer rasters to the point class created above 
        ExtractMultiValuesToPoints(inPoints, rasterList)

        arcpy.AddMessage("Deleting intermediate rasters...")
        for raster in rasterList:
            arcpy.management.Delete(raster)

        arcpy.env.workspace = outputWorkspace
        
        # spatial join the point class (with data from rasters) to the vector grid above
        outFC = nameVariable + "_pu_Aligned"  # name of new polygon class denoted with attributed
        arcpy.analysis.SpatialJoin(inPolygons, inPoints, outFC)
        
        
        arcpy.AddMessage("Deleting intermediate polygons...")
        arcpy.management.Delete(inPoints)
        arcpy.management.Delete(inPolygons)
        
        arcpy.AddMessage("Deleting blank rows...")
        
        outFC_path = os.path.join(outputWorkspace,outFC)
        checkRows = arcpy.UpdateCursor(outFC_path)
        outFields = arcpy.ListFields(outFC_path)
        
        #delete all rows with null or 0 values across all fields in keepField_List
        for row in checkRows:
            total = 0.0
            for field in outFields:
                for keep in keepField_List:
                    if keep in field.name:
                        value = row.getValue(field.name)
                        if value is None or value == 0.0:
                            pass
                        else:
                            total += row.getValue(field.name)
                else: 
                    continue
            
            if total == 0.0:
                checkRows.deleteRow(row)
                
        arcpy.AddMessage("Output feature class: "+outFC)
        del fields, inPolygons, outFC, rasterList, inPoints
        

        return

        ################################# END OF STEP 1 ###################################

class AreaWeight(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Area Weighting"
        self.description = """The second step of the data preparation toolbox can be used for activity feature
        classes that are in vector grids that have larger cell sizes compared to the reference vector grid 
        (e.g., 10x10 km grids vs 1x1 km grids), and/or are polygon features that are not vector grids.
 
        The activity feature class will be clipped to the coastline and study area and a new field for 
        "Activity Marine Area" will be calculated using shape geometry. Then the clipped data is intersected 
        with the planning unit grid to apply the data to the planning unit grid. The activity area weight 
        is calculated by dividing the planning unit grid area by the activity marine area. Finally, the 
        adjusted intensity attribute is calculated by multiplying intensity by the activity area weight.

        The result is the distribution of relative intensity values by area to prevent double counting of 
        calculated impact across planning units. The output feature class will be named with a suffix 
        "pu_aligned", and the area weighted or "adjusted" relative intensity fields will be named with a 
        prefix: "ADJ_"."""
        
        self.canRunInBackground = False

    def getParameterInfo(self):
        ##  Define parameters

        param0 = arcpy.Parameter(
            displayName="Output workspace",
            name="outputWorkspace",
            datatype=["DEWorkspace","DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Actvity Feature Class",
            name="inFC",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Activity Limits Feature Dataset",
            name="inDS",
            datatype="DEFeatureDataset",
            parameterType="Required",
            direction="Input")
        param2.value=os.path.join(os.path.dirname(__file__), r'CI_InputData.gdb\activity_limits')
     
        param3 = arcpy.Parameter(
            displayName="Activity Limits Feature Class",
            name="inLimit",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param4 = arcpy.Parameter(
            displayName="Planning Unit Grid",
            name="inPlnUnit",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")
        param4.value = os.path.join(os.path.dirname(__file__), r'CI_InputData.gdb\baselayers\pu_1km_Marine')

        param5 = arcpy.Parameter(
            displayName="Intensity Field",
            name="inField",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Output Coordinate System",
            name="outCoordSys",
            datatype="GPSpatialReference",
            parameterType="Required",
            direction="Input")
        
        param7 = arcpy.Parameter(
            displayName="Run Pairwise Intersect",
            name="pairwise",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param7.value = True

        parameters = [param0,param1,param2,param3,param4,param5,param6, param7]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        
        #create a list of feature classes for user to choose an activity limit
        if parameters[2].value: #must be .value in order to populate list with feature class objects and not string. DO NOT USE .valueAsText
            arcpy.env.workspace = parameters[2].value
            FCs = arcpy.ListFeatureClasses(parameters[2].value) #must be .value in order to populate list with feature class objects and not string. DO NOT USE .valueAsText
            fcList = []
            for fc in FCs:
                fcList.append(fc)
            parameters[3].filter.list=sorted(fcList)
            
            
       #create a list of fields in the input dataset to have user specify intensity attribute
        if parameters[1].valueAsText:
            fields=arcpy.ListFields(parameters[1].valueAsText)
            fieldList = []
            for f in fields:
                fieldList.append(f.name)
            parameters[5].filter.list=sorted(fieldList)


        return
            

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        ##  The source code of the tool.
        outputWorkspace = parameters[0].valueAsText  # workspace where new layers will be saved
        inFC = parameters[1].valueAsText  # data layer containing data to be area weighted
        inDS = parameters[2].valueAsText  # feature dataset containing limiting layers
        inLimit = parameters[3].value # limiting layer to be clipped to
        inPlnUnit = parameters[4].valueAsText  # planning unit grid at desired resolution
        inField = parameters[5].valueAsText  # Field used to calculate intensity
        outCoordSys = parameters[6].value  # desired coordinate system for outputs
        pairwise = parameters[7].value # indicator for pairwise intersect analysis

        # set workspace
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = outputWorkspace

        arcpy.AddMessage("Output workspace: "+str(outputWorkspace))

        # clip the input layer to the coastline
        clipBoundary = os.path.join(inDS,inLimit)
        arcpy.AddMessage(clipBoundary)
        #inFC includes the full path 
        inFCname = os.path.split(inFC)[1]
        clipFCname = str(inFCname)+"_Coast_Clipped"

        arcpy.AddMessage("Clipping " + str(inFC)+" to coastline...")
        clipFC = arcpy.analysis.PairwiseClip(inFC, clipBoundary, os.path.join(outputWorkspace,clipFCname))
        
        #run repair geometry after clipping to catch any errors created during clip
        arcpy.AddMessage("Repairing geometry...")
        arcpy.management.RepairGeometry(clipFC)
        #messages.addGPMessages()
                                             
        # add new field for activity marine area and calculate geometry
        fieldAMA = "Activity_MarineAREA"
        arcpy.AddMessage("Calculating "+str(fieldAMA) + "...")
        arcpy.management.AddField(clipFC, "Activity_MarineAREA", "DOUBLE", None, None, None, '', "NULLABLE", "NON_REQUIRED", '')
        arcpy.management.CalculateGeometryAttributes(clipFC, "Activity_MarineAREA AREA", '', "SQUARE_METERS", outCoordSys)
        
        # intersect the clipped layer with the marine planning unit
        inFCname = os.path.split(inFC)[1]
        intersectFCName = str(inFCname)+"_"+inLimit+"_Weighted"
        
        arcpy.AddMessage("Intersecting input feature class with reference vector grid...")
        if pairwise == True:
            arcpy.AddMessage("Running Pairwise Intersect...")
            intersectFC = arcpy.analysis.PairwiseIntersect([clipFC, inPlnUnit], intersectFCName)
        else:
            arcpy.AddMessage("Running Intersect Analysis...")
            intersectFC = arcpy.analysis.Intersect([clipFC, inPlnUnit], intersectFCName)
                
        # add new field and calculate pu activity marine area
        fieldPUAMA = "pu_Activity_MarineAREA"
        arcpy.AddMessage("Adding field: "+str(fieldPUAMA))
        arcpy.management.AddField(intersectFC, "pu_Activity_MarineAREA", "DOUBLE", None, None, None, '', "NULLABLE", "NON_REQUIRED",'')
        arcpy.management.CalculateGeometryAttributes(intersectFC, "PU_Activity_MarineAREA AREA", '', "SQUARE_METERS", outCoordSys)
        
        # Calculate Activity Area Weight
        arcpy.AddMessage("Calculating activity area weight...")
        expression1 = "!pu_Activity_MarineArea!/!Activity_MarineAREA!"
        arcpy.management.CalculateField(intersectFC, "Activity_MarineAREA_WT", expression1, "PYTHON3", "", "FLOAT")
        
        # Calculate Intensity Field
        expression2 = "!"+inField+"!*!Activity_MarineAREA_WT!"
        intensityField = "ADJ_"+str(inField)
        arcpy.AddMessage("Calculating area weighted intensity field: "+str(intensityField))
        arcpy.management.CalculateField(intersectFC, intensityField, expression2, "PYTHON3", "", "FLOAT")
        
        del clipFC, intersectFC
        arcpy.AddMessage("Output feature class: "+str(intersectFCName))
        
        return
        ################################# END OF STEP 2 ###################################

class AddActivityFields(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3. Add Activity Fields"
        self.description = """The final step in the Data Preparation Toolbox can be used to add 
                        fields to the input activity feature class that will be required in the 
                        Cumulative Impact Mapping analysis. The fields that will be added are:
                        •	ACTIVITY_CODE
                        •	Sub_Activity
                        •	STRESSOR_CODE
                        These fields will be populated using values from the master stressor table. 
                        Please ensure that the codes for each activity are consistent across all the
                        input tables ("master_stressor_table", "vscores_habitats", "fishing_severity").
                        
                        The output feature class will be named using the scenario selected as a prefix 
                        to the activity code selected and saved in the appropriate input workspace for 
                        the Cumulative Impact Mapping Analysis. 
                        
                        In the sample data, the recommended workspaces are :
                        •	CI_Coastal_Inputs.gdb - for all marine based coastal data 
                        •	CI_Land_Inputs.gdb - for all land-based data (both coastal and in the major watersheds) 
                        •	CI_MarineFootprint_Inputs.gdb - for all marine datasets with large area footprints."""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName = "Activity Feature Class",
            name ="inFC",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName = "Activity Code",
            name ="inAct",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        param2 = arcpy.Parameter(
            displayName = "Subactivity Field",
            name ="inSub",
            datatype = "GPString",
            parameterType="Required",
            direction="Input")


        param3 = arcpy.Parameter(
            displayName = "Master Stressor Table",
            name ="masterStressorTable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        param3.value = os.path.join(os.path.dirname(__file__), r'CI_InputData.gdb\master_stressor_table')
        
        param4 = arcpy.Parameter(
            displayName = "Output Workspace",
            name ="outputWorkspace",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param4.filter.list = [os.path.join(os.path.dirname(__file__),r'CI_MarineFootprint_Inputs.gdb\inputs'), 
                              os.path.join(os.path.dirname(__file__),r'CI_Land_Inputs.gdb\inputs'), 
                              os.path.join(os.path.dirname(__file__),r'CI_Coastal_Inputs.gdb\inputs')]

        param5 = arcpy.Parameter(
            displayName = "Scenario",
            name ="scn",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param5.filter.list = ["c",'f',"p"]

        param6 = arcpy.Parameter(
            displayName = "Intermediate Workspace",
            name = "intermedWorkspace",
            datatype = ["DEWorkspace","DEFeatureDataset"],
            parameterType = "Required",
            direction = "Input"
        )
        #param6.filter.list = ["Commercial Fishing (Not including sport fishing)", "Marine", "Coastal", "Land"]

        parameters = [param0, param1, param2, param3, param4, param5, param6]
        return parameters


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        #pull list of activities from master stressor table
        if parameters[3].valueAsText:
            activities = set()
            subactivities = set()
            rows1 = arcpy.da.SearchCursor(parameters[3].valueAsText,["ACTIVITY_CODE"])
            for row in rows1:
                activities.add(row[0])
            del rows1
            parameters[1].filter.list=sorted(list(activities))

            #after the activity feature class is selected, populate a list of fields and add to a set so the user can select the field that contains the sub-activity
            if parameters[0].valueAsText:
                inFC = parameters[0].valueAsText
                #create describe object to get list of fieldnames
                desc = arcpy.Describe(inFC)
                for field in desc.fields:
                    subactivities.add(field.name)
                sortedFieldList = sorted(subactivities)
                sortedFieldList.insert(0, "No Sub-activity Field")
                parameters[2].filter.list=sortedFieldList
                if "Sub_Activity" in subactivities:
                    parameters[2].value = "Sub_Activity"                        

        
        
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
        # add warning if user has not selected a subactivity field that it will apply none automatically
        if parameters[0].valueAsText:
            if parameters[2].valueAsText is None:
                parameters[2].setWarningMessage("No Sub-activity is selected, default value of 'None' will be applied if a Sub-activity field is not selected.")
            elif parameters[2].valueAsText == "Sub_Activity":
                parameters[2].setWarningMessage("A 'Sub_Activity' field exists in your feature class and will be used by default. If you would like to use a different field to represent sub activity, please delete or rename 'Sub_Activity' field prior to running the tool.")
        
        
        # add error if output workspace does not exist
        if parameters[4].altered:
            outputworkspace = parameters[4].valueAsText
            if arcpy.Exists(outputworkspace) == False:
                parameters[4].setErrorMessage("The output workspace you have selected does not exist. Please create the gdb and feature dataset called 'inputs' using the spatial reference of the datasets in CI_InputData.gdb.")
                    
        
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        #Load Parameters
        inFC = parameters[0].value  #feaure class path
        inAct = parameters[1].valueAsText
        inSubAct = parameters[2].valueAsText
        masterStressorTable = parameters[3].valueAsText
        outputWorkspace = parameters[4].valueAsText
        scn = parameters[5].valueAsText
        intermedWorkspace = parameters[6].valueAsText

        # #Change the output workspace based on the sector that the user identifies that the activity belongs to
        # if sector == "Commercial Fishing (Not including sport fishing)":
        #     arcpy.env.workspace = os.path.join(os.path.dirname(__file__),r'CI_Data_Prep\Fishing\Intermediates.gdb')
        # elif sector == "Marine":
        #     arcpy.env.workspace = os.path.join(os.path.dirname(__file__),r'CI_Data_Prep\Marine\Intermediates.gdb')
        # elif sector == "Land":
        #     arcpy.env.workspace = os.path.join(os.path.dirname(__file__),r'CI_Data_Prep\Land\Intermediates.gdb')
        # elif sector == "Coastal":
        #     arcpy.env.workspace = os.path.join(os.path.dirname(__file__),r'CI_Data_Prep\Coastal\Intermediates.gdb')        
        
        # inputWorkspace = os.path.dirname(parameters[0].valueAsText)

        arcpy.env.workspace = intermedWorkspace
        
        #make a copy of the updated table with appropriate name and save to CI toolbox inputs gdb    
        copyFC = scn+"_"+os.path.basename(inAct)
        arcpy.AddMessage("Processing "+copyFC+"...")
        #arcpy.management.CopyFeatures(inFC, copyFC)
        
        inputWorkspace = os.path.join(os.path.dirname(parameters[0].valueAsText))
        arcpy.AddMessage("Input workspace: "+inputWorkspace)
        arcpy.AddMessage("Intermediate workspace: "+intermedWorkspace)
        arcpy.AddMessage("Output workspace: "+outputWorkspace)
        if inputWorkspace==outputWorkspace:
            outFC = inFC
            arcpy.env.workspace = outputWorkspace
        else:
            arcpy.env.workspace = intermedWorkspace
        
            #make a copy of the updated table with appropriate name and save to CI toolbox inputs gdb    
            copyFC = scn+"_"+inAct
            arcpy.AddMessage("Copying features to new workspace...")
            outFC = arcpy.management.CopyFeatures(inFC, copyFC)
        

        #define list of fields to be added to the output feature class
        fieldParams = [("ACTIVITY_CODE", "STRING"), ("Sub_Activity","STRING"), ("STRESSOR_CODE","STRING"), ("Stressor_WT","DOUBLE") ]

        #iterate through list of new fields and systematically add them to the output feature class.
        for p in fieldParams:
            arcpy.management.AddField(outFC, p[0], p[1], "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            
            arcpy.AddMessage("        Adding fields: "+str(p))

        #Copy user defined "SubActivity" field to field called "Sub_Activity"
        if inSubAct != "Sub_Activity":
            arcpy.AddMessage("Copying sub activity field to 'Sub_Activity'...")
            subfield = "Sub_Activity"
            if inSubAct == "No Sub-activity Field":
                arcpy.management.CalculateField(outFC, subfield, "None", "PYTHON3", "", "TEXT")
            else:
                arcpy.management.CalculateField(outFC, subfield, inSubAct, "PYTHON3", "", "TEXT")

        
        ##set fields to build dictionaries for stressor code and stressor weight

        dictFields=(["ACTIVITY_CODE", "Sub_Activity","STRESSOR_CODE","Stressor_WT"])

        ##search cursor to populate dictionaries for two variables to be collected: Stressor Code and Stressor Weight
        dictCursor = arcpy.da.SearchCursor(masterStressorTable,dictFields)
        stressorDict = {}
        weightDict = {}
        
        #region Glossary for search cursor:
        # row[0] = ACTIVITY_CODE
        # row[1] = Sub_Activity
        # row[2] = STRESSOR_CODE
        # row[3] = Stressor_WT
        #endregion

        #pair activity code and subactivity to stressor code, and activity code and subactivity code to stressor weight
        for row in dictCursor:
            #limit dictionary updates to only stressors and stressor weights that are related to the activity
            if row[0] == inAct:
                stressorDict.update({str(row[0])+","+str(row[1]):str(row[2])})
                weightDict.update({str(row[0])+","+str(row[1]):str(row[3])})     
        del dictCursor
        arcpy.AddMessage("Stressors applied (by Sub_Activity):")
        arcpy.AddMessage(stressorDict)
        arcpy.AddMessage("Stressor weights applied (by Sub_Activity):")
        arcpy.AddMessage(weightDict)
        
        
        #Set the fields for the update cursor to use to update the output feature class with stressor codes and stressor weights
        updateFields = (["ACTIVITY_CODE", "Sub_Activity","STRESSOR_CODE", "Stressor_WT"])
        arcpy.AddMessage("Calculating fields: "+str(updateFields))

        updCursor = arcpy.da.UpdateCursor(outFC, updateFields)
        
        #region Glossary for Update Cursor:
        #row[0] = ACTIVITY_CODE
        #row[1] = Sub_Activity
        #row[2] = STRESSOR_CODE
        #row[3] = Stressor_WT
        #endregion
        
        for row in updCursor:
            row[0] = inAct
            subact = str(row[1])
            # if user leaves subactivity blank, default to "None"
            if subact is None or subact.upper() == "NONE":
                row[1] = "None"
                
            ### LOGIC CHECK Selina July 19 - if None NONE NoNE = Upper ????  

            #set a keyvalue to look up in the dictionary and grab the stressor code and stressor weight values based on the activity and subactivity
            stressorKey = str(row[0])+","+str(row[1])
            #Set Stressor code equal to dictionary entry at the key value
            if stressorKey in stressorDict:
                row[2] = stressorDict[stressorKey]
            #Set Stressor weight equal to dictionary entry at the key value
            if stressorKey in weightDict:
                row[3] = weightDict[stressorKey]

            updCursor.updateRow(row)
        del updCursor

        if inputWorkspace != outputWorkspace:
            #if copyFC exists in outputWorkspce, delete first
            finalFC = os.path.join(outputWorkspace,scn+"_"+inAct)
            #arcpy.AddMessage(finalFC)
            if arcpy.Exists(finalFC):
                arcpy.management.Delete(finalFC)
                arcpy.AddMessage("Overwriting existing activity feature class...")

            #export final FC to output geodatabase selected by activity code
            #finalFC = os.path.join(outputWorkspace,os.path.basename(copyFC))
            finalFC = os.path.join(outputWorkspace,scn+"_"+inAct)
            arcpy.env.workspace = outputWorkspace
            arcpy.management.CopyFeatures(outFC, finalFC)
            arcpy.AddMessage("Output feature class: "+finalFC)


        return

    
