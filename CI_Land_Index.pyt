# -*- coding: utf-8 -*-

import arcpy, os
from arcpy.sa import *


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        
        self.label = "Land Index Toolbox"
        self.alias = "LandIndex"
        self.description = """The Land Index toolbox processes land-based activity data, depending on 
        whether the activities occur within the boundaries of major watersheds, or whether the activities
        occur in coastal areas within impact distance of the ocean. The outputs of both tools will be pulled
        into the Coastal Kernel Density analysis at Step 3.
        
        Step 1a is used for activity data that falls within major watersheds of stream order 7 or higher. 
        These represent the most significant river systems and data from the headwaters of each drainage 
        basin is included. A Land index (LI) value will be saved to point features representing the main
        estuaries of each major watershed. These points are then used in the coastal kernel density tool
        to determine impact.
        
        Step 1b is used to process coastal land-based activity data that falls within coastal watersheds 
        of stream order less than 7. The Cumulative Impact Mapping analysis will model the impact of these
        land-based activities within a specified impact distance from the coastline."""
        
        # List of tool classes associated with this toolbox
        self.tools = [Step1A, Step1B]

class Step1A(object):
    
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1a. Calculate Land Index (LI) for activities in major watersheds"
        self.description = """Step 1a is used to process land-based activity data that falls within major 
        watersheds with stream order 7 or higher. These represent the most significant river systems and 
        data from the headwaters of each drainage basin is included.
         
        The Land Index (LI) is calculated by summing the relative intensity field, dividing the result by 
        the area of the watershed, and multiplying the value by 10,000 to avoid infinitesimal LI values. 
        
        If no relative intensity field is available, the shape geometry of the feature class can be used 
        to calculate the LI: 
        •	Points -  no. of points / watershed area
        •	Lines - length of lines / watershed area
        •	Polygons -  area of polygons / watershed area. 
        
        The LI value will then be saved to the point feature representing the main estuary of the watershed. 
        The output feature class will be named with the scenario and activity code and saved in the Output 
        Workspace: "DFO_CI_Toolbox\CI_Coastal_Inputs.gdb\inputs". These estuary points are then used as input
        features for the coastal kernel density tool to model decreasing impact from the estuary up to a maximum
        impact distance."""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        param0 = arcpy.Parameter(
            displayName = "Input Workspace",
            name = "inputWorkspace",
            datatype = ["DEWorkspace","DEFeatureDataset"],
            parameterType="Required",
            direction = "Input"
        )
        param0.value = os.path.join(os.path.dirname(__file__),r'CI_Land_Inputs.gdb\inputs')
        
        param1 = arcpy.Parameter(
            displayName = "Output Workspace",
            name = "outputWorkspace",
            datatype = ["DEWorkspace","DEFeatureDataset"],
            parameterType="Required",
            direction = "Input"
        )
        param1.value = os.path.join(os.path.dirname(__file__),r'CI_Coastal_Inputs.gdb\inputs')
        
        param2 = arcpy.Parameter(
            displayName="Input Feature Class",
            name = "inputFC",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        param3 = arcpy.Parameter(
            displayName = "Master Stressor Table",
            name = "stressorTable",
            datatype = "DETable",
            parameterType = "Required",
            direction = "Input"
        )
        param3.value = os.path.join(os.path.dirname(__file__), r'CI_InputData.gdb\master_stressor_table')
 
        param4 = arcpy.Parameter(
            displayName = "Intensity Attribute",
            name="intensity",
            datatype = "GPString",
            parameterType="Required",
            direction = "Input"
        )

        param5 = arcpy.Parameter(
            displayName = "Major Watersheds",
            name = "watersheds",
            datatype = "DEFeatureClass",
            parameterType = "Required",
            direction = "Input"
        )
        param5.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\baselayers\Land_Watersheds')
        
        param6 = arcpy.Parameter(
            displayName="Estuary Points",
            name = "estuaries",
            datatype = "DEFeatureClass",
            parameterType="Required",
            direction = "Input"
        )
        param6.value = os.path.join(os.path.dirname(__file__), r'CI_InputData.gdb\baselayers\Estuary_Watershed')

        param7 = arcpy.Parameter(
            displayName="Case attributes for summary statistics",
            name = "caseFields",
            datatype = "GPString",
            parameterType ="Required",
            direction = "Input",
            multiValue="True"
        )
        param7.value = ["WSHD_ID","WATERSHED_AREA"]

        param8 = arcpy.Parameter(
            displayName = "Intermediate Workspace",
            name = "intermedWorkspace",
            datatype = ["DEWorkspace","DEFeatureDataset"],
            parameterType = "Required",
            direction = "Input"
        )
        param8.value = os.path.join(os.path.dirname(__file__), "CI_Land_Inputs.gdb\Intermediates")
        
        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        
        if parameters[0].value:
            inputworkspace =  parameters[0].valueAsText
            arcpy.env.workspace = inputworkspace
            fcList = arcpy.ListFeatureClasses("*lnd*")
            parameters[2].filter.list = fcList
        
        #pull list of activities from master stressor table
        if parameters[3].valueAsText:
            activities = set()

            rows1 = arcpy.da.SearchCursor(parameters[3].valueAsText,["ACTIVITY_CODE"])
            for row in rows1:
                if "lnd" in row[0]:
                    activities.add(row[0])
            del rows1

        # create dropdown list of fields for user to specify the intensity attribute
        if parameters[2].altered:
            if parameters[2]:
                fields = arcpy.ListFields(parameters[2].valueAsText)
                intensityFieldList = []

                for f in fields:
                    intensityFieldList.append(f.name)
                
                sorted_intensityFieldList = sorted(intensityFieldList)
                sorted_intensityFieldList.insert(0, "Use shape geometry to calculate LI")
                parameters[4].filter.list = sorted_intensityFieldList
            if parameters[5]:
                caseFields=arcpy.ListFields(parameters[5].valueAsText)
                caseList = []
                for case in caseFields:
                    caseList.append(case.name)
                parameters[7].filter.list=sorted(caseList)
                
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
    
    # initialize parameters
        inputWorkspace = parameters[0].valueAsText
        outputWorkspace = parameters[1].valueAsText
        inputFC =parameters[2].valueAsText
        stressorTable = parameters[3].valueAsText
        intensity = parameters[4].valueAsText
        watersheds = parameters[5].valueAsText
        estuaries = parameters[6].valueAsText
        caseFields = parameters[7].valueAsText
        intermedWorkspace = parameters[8].valueAsText

        #set environments
        arcpy.env.workspace = outputWorkspace
        arcpy.AddMessage("Output workspace: "+str(outputWorkspace))
        

        ##  Grab the activity code from the input feature

        #split inputFC into scenario and activity code. use the tail (activity code) to assign activity code 
        scenario = inputFC[:1]
        actCode = inputFC[2:]
        
        #inFC = full path to feature class
        inFC = os.path.join(inputWorkspace, inputFC)

        arcpy.AddMessage("Processing "+str(inputFC)+"...")
        
        #fill list of stressors associated with the selected activity code
        stressors = set()
        stressorSearch = arcpy.da.SearchCursor(stressorTable,["ACTIVITY_CODE","STRESSOR_CODE"])
        #region Glossary for stressor identifying cursor
        #row[0] = ACTIVITY_CODE
        #row[1] = STRESSOR_CODE
        #endregion
        for row in stressorSearch:
                if row[0] == actCode:
                    stressors.add(row[1])

        #create describe object to determine geography of the input FC
        describe = arcpy.Describe(inFC)
        geometryType = describe.shapeType
        arcpy.AddMessage("Feature class geometry: " + str(geometryType))    
        
        
        #set default intensity attribute based on geometry if user does not specify an intensity
        if intensity == "Use shape geometry to calculate LI":
            arcpy.AddMessage("Using shape geometry to calculate Land Index...")
            #point data with no assigned intensity needs a new intensity field to calculate stressor weighted intensity. To differentiate from assigned intensities, the attribute is called "Point_Count" 
            if geometryType == "Point":    
                intensity = "Point_Count" #to be used as a new attribute in point data with no intensity in database
                
                #create field for "Point_Count" (absence/presence) and populate the field with 1 for each point in dataset
                arcpy.management.AddField(inFC,"Point_Count","DOUBLE")
                arcpy.management.CalculateField(inFC, "Point_Count", 1.0)
                arcpy.AddMessage("Land index will be calculated using 'Point_Count'.")
            
            else:
                #Assign intensity field based on geometry
                #case for line data
                if geometryType =="Line" or geometryType=="Polyline":
                    #add field for land index calculated length
                    arcpy.management.AddField(inFC, "LI_Length","DOUBLE")
                    #calculate length based on FC geometry
                    arcpy.management.CalculateGeometryAttributes(inFC, "LI_Length LENGTH", "METERS")
                    intensity = "LI_Length"
                    
                #case for polygon data
                if geometryType =="Polygon":
                    #add field for land index calculated area
                    arcpy.management.AddField(inFC, "LI_Area","DOUBLE")
                    #calculate area based on FC geometry
                    arcpy.management.CalculateGeometryAttributes(inFC, "LI_Area AREA", '', "SQUARE_METERS")
                    intensity = "LI_Area"
                    
                
                arcpy.AddMessage("Land index will be calculated using: " +str(intensity))




    # Summarize stressor weighted activity data to watersheds
        #create a single copy of the estuary points to use as output FC in the target gdb.
        outFCname = scenario+"_"+actCode
        outputPath = os.path.join(outputWorkspace,outFCname)

        #Check to see if output already exists in output database and if it does, delete it prior to copying the estuary dataset
        if arcpy.Exists(outputPath):
            arcpy.management.Delete(outputPath)
            arcpy.AddMessage("Overwriting exisiting RI feature class...")
        
        #create a copy of the estuary dataset as the final ouput
        outputFC = arcpy.management.Copy(estuaries,outputPath)

        #for each relevant stressor, add a field for RI and stressor weighted RI
        for s in stressors:
            arcpy.AddMessage("Processing "+s+"...")
            
            #add fields used in Stressor weighting calculation
            arcpy.management.AddField(inFC, "RI", "DOUBLE")
            arcpy.management.AddField(inFC,"RI_"+s, "DOUBLE")
            
            #copy intensity field to "RI" field
            arcpy.management.CalculateField(inFC, "RI","!"+intensity+"!")
            
            arcpy.AddMessage("Calculating 'RI' and 'RI_"+s+"'...")
            #update cursor to calculate stressor weighted intensity
            weightCursor = arcpy.da.UpdateCursor(inFC, ["RI", "RI_"+s, "STRESSOR_CODE", "Stressor_WT"])
            #region Glossary for weighting cursor
            #row[0] = RI
            #row[1] = RI_s
            #row[2] = STRESSOR_CODE
            #row[3] = Stressor_WT
            #endregion
            for weightRow in weightCursor:
                if s == weightRow[2]:
                    weightRow[1] = weightRow[0] * weightRow[3]
                    weightCursor.updateRow(weightRow)
            del weightCursor


            #apply calculated RI_s, LI_s and relevant codes to the output FC for each stressor
            arcpy.env.workspace = intermedWorkspace
            arcpy.AddMessage("Intermediate workspace: "+intermedWorkspace)
            
            #if intermed workspace == feature dataset, move arc.env.workspace up to gdb. 
            desc_intermedWorkspace = arcpy.Describe(intermedWorkspace)
            if desc_intermedWorkspace.dataType == 'FeatureDataset':
                tableWorkspace = os.path.dirname(intermedWorkspace)
            else:
                tableWorkspace = intermedWorkspace
            arcpy.AddMessage("Intermediate workspace for tables: "+tableWorkspace)
            
            #set up intersection and summary
            #set variables for intersect tool
            intersectName =scenario +"_"+actCode+"_"+s+"_intersect"
            sumTableName = scenario +"_"+actCode+"_"+s+"_statistics"
            sumField = [("RI_"+s, "SUM")]
            sumPath = os.path.join(tableWorkspace, sumTableName)
            
            #select only features where the stressor code is s
            where_clause = "STRESSOR_CODE = '{}'".format(s)
            selectedFC = arcpy.management.SelectLayerByAttribute(inFC, "NEW_SELECTION", where_clause)

            arcpy.AddMessage("Intersecting "+actCode+" with watersheds...")            
            #intersect FC with Land Watersheds and calculate summary statistics of stressor weighted intensity
            intersectFC = arcpy.analysis.Intersect([selectedFC, watersheds], intersectName)

            arcpy.env.workspace = tableWorkspace
            summaryTable = arcpy.analysis.Statistics(intersectFC, sumTableName, sumField, caseFields)
            
            #LOGIC CHECK: add a field for LI so that it can be calculated on the summary to come
            arcpy.management.AddField(summaryTable, "LI_"+s,"DOUBLE")


    # Calculate Land Index (LI): population attibute for Kernel Density Analysis tool
            arcpy.env.workspace = outputWorkspace

            LIFields = ["LI_"+s,"SUM_RI_"+s, "WATERSHED_AREA"]
            #set path to summary table created above
            
            #region Glossary for LI Calculation:
            #row[0] = LI (index to be calculated)
            #row[1] = SUM_RI_s (watershed summed stressor weighted intensity)
            #row[2] = WATERSHED_AREA (area of watershed)
            #endregion

            arcpy.AddMessage("Calculating 'LI_"+s+"'...")
            #calculate LI by Sum_RI_s divided by the associated watershed area
            LICursor = arcpy.da.UpdateCursor(sumPath, LIFields)
            for row in LICursor:
                row[0] = 100000*(row[1]/row[2])
                LICursor.updateRow(row)
            del LICursor

            # Add field for land index and activity/stressor/subactivity codes to estuary dataset
            fieldParams = [("LI_"+s, "DOUBLE"),["SUM_RI_"+s, "DOUBLE"],("ACTIVITY_CODE","STRING"),("STRESSOR_CODE","STRING")]
        
            for p in fieldParams:
                arcpy.management.AddField(outputFC, p[0], p[1], "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            
            #create value dictionary of all watershed ID and corresponding intensity from summarized activity
            #use WSHD_ID to join 
            SUM_RIDict = {}
            LIDict = {}
            watershedCursor = arcpy.da.SearchCursor(summaryTable, ["WSHD_ID", "SUM_RI_"+s, "LI_"+s])
            for row in watershedCursor:
                SUM_RIDict.update({row[0]:row[1]})
                LIDict.update({row[0]:row[2]})
            del watershedCursor
    
            arcpy.AddMessage("Saving 'LI_"+s+"' to output feature class...")
            # Copy LI and RI from summary table to estuary points based on Watershed ID
            intensityFields = ["WSHD_ID", "SUM_RI_"+s, "LI_"+s,"ACTIVITY_CODE", "STRESSOR_CODE"]
            intensityLICursor = arcpy.da.UpdateCursor(outputFC, intensityFields)            
            #row[0] = watershed ID (used as key value to apply intensity value)   
            #row[1] = "SUM_RI_"+s: sum of intensity attribute within watershed (from watershed summary)
            #row[2] = "LI_"+s: Land index value (calculated in summary stats table, pulled from table)
            #row[3] = activity code (to be used in further steps)
            #row[4] = stressor code


            for row in intensityLICursor:
                intensityKey = row[0] # use watershed ID to locate associated intensity
                
                #arcpy.AddMessage("Watershed ID is: "+str(intensityKey))
        
                if intensityKey in SUM_RIDict:
                    row[1] = SUM_RIDict[intensityKey] #set sum intensity from dictionary of intensity values
                if intensityKey in LIDict:
                    row[2] = LIDict[intensityKey] #set LI from dictionary of LI_s values

                row[3] = actCode #assign activity code from parameter
                row[4] = s #assign stressor code from current stressor
                
                intensityLICursor.updateRow(row)

            del intensityLICursor
        
        arcpy.AddMessage("Output Feature Class: ")
        arcpy.AddMessage(outputFC)   



        return
########################################### END OF STEP 1A #################################################################
class Step1B(object):    
    
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1b. Intersect coastal land-based activities with Coastal Watersheds"
        self.description = """Step 1b is used to process coastal land-based activity data that falls within
        coastal watersheds of stream order less than 7. The Cumulative Impact Mapping analysis will model
        the impact of these land-based activities within a specified impact distance from the coastline. 
        
        The tool will intersect the activity data with the coastal watersheds and the output feature classes, 
        named with user-specified scenario and activity codes will be saved in the Output Workspace: 
        "CI_Coastal_Inputs.gdb\inputs" to be run through the Coastal Kernel Density toolbox."""
        
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        param0 = arcpy.Parameter(
            displayName = "Input Workspace",
            name = "inputWorkspace",
            datatype = ["DEWorkspace","DEFeatureDataset"],
            parameterType="Required",
            direction = "Input"
        )
        param0.value = os.path.join(os.path.dirname(__file__),r'CI_Land_Inputs.gdb\inputs')    
            
        param1 = arcpy.Parameter(
            displayName = "Output Workspace",
            name = "outputWorkspace",
            datatype = ["DEWorkspace","DEFeatureDataset"],
            parameterType="Required",
            direction = "Input"
        )
        param1.value = os.path.join(os.path.dirname(__file__),r'CI_Coastal_Inputs.gdb\inputs')
        
        param2 = arcpy.Parameter(
            displayName = "Input feature class (Activity)",
            name = "inputFC",
            datatype="GPString",
            parameterType = "Required",
            direction="Input"
        )
        
        param3 = arcpy.Parameter(
            displayName = "Coastal Watersheds",
            name = "watersheds",
            datatype="DEFeatureClass",
            parameterType = "Required",
            direction = "Input"
        )
        param3.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\baselayers\Coast_Watersheds')
        
        # param3 = arcpy.Parameter(
        #     displayName = "Scenario",
        #     name = "Scenario",
        #     datatype = "GPString",
        #     parameterType="Required",
        #     direction = "Input"
        # )
        # param3.filter.list = ["c","f","p"]
        
        params = [param0, param1,param2, param3]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[0].value:
            inputworkspace =  parameters[0].valueAsText
            arcpy.env.workspace = inputworkspace
            fcList = arcpy.ListFeatureClasses("*cst*")
            parameters[2].filter.list = fcList


        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
    
        #initialize parameters
        inputWorkspace = parameters[0].valueAsText
        outputWorkspace = parameters[1].valueAsText
        inputFC = parameters[2].valueAsText
        watersheds = parameters[3].valueAsText
        # scenario = 
        
        #split inputFC into scenario and activity code. use the tail (activity code) to assign activity code 
        scenario = inputFC[:1]
        actCode = inputFC[2:]
        
        #inFC = full path to feature class
        inFC = os.path.join(inputWorkspace, inputFC)

        arcpy.AddMessage("Processing "+str(inputFC)+"...")
        

        #set output Workspace
        arcpy.env.workspace = outputWorkspace
        arcpy.AddMessage("Output workspace: "+outputWorkspace)
        
        ##  Grab the activity code from the input feature
        #split pathname into 
        actPathTail = os.path.split(inFC)[1]
        actCode = actPathTail[2:]

        #Set features to be intersected (activity and watersheds)
        intersectFeatures = [inFC, watersheds]
        #set name of output to be put in the target GDB 
        outFC = scenario + "_" + actCode

        arcpy.AddMessage("Intersecting "+actCode+" with coastal watersheds...")
        #intersect activity FC with estuaries FC
        arcpy.analysis.PairwiseIntersect(intersectFeatures, outFC)
        
        arcpy.AddMessage("Output feature class: "+outFC)

        return