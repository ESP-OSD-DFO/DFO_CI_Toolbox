# -*- coding: utf-8 -*-

import arcpy, os, math, random, sys
from arcpy.sa import *
from arcpy.ia import *


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        
        self.label = "Coastal Kernel Density Toolbox"
        self.alias = "CoastalKD"
        self.description = """The Coastal Kernel Density Toolbox models decreasing relative intensity of a stressor around a
        point/line source activity with increasing distance, up to a maximum distance. This toolbox will 
        run the coastal kernel density analysis for all coastal marine activities, coastal land-based activities,
        and land-based activities in major watersheds (represented by Land Index values at estuaries).
         
        Land-based activities represented at estuary points will have impact distances based on stream order 
        and coastal activities with multiple or different stressors per sub-activity will have impact distances 
        noted in the master stressor table.  
        
        The Coastal KD Toolbox outputs will be saved in the Wtd_RI feature dataset of the CI_MarineFootprint_Inputs.gdb,
        for insertion into the Marine Footprint Toolbox at Step3.
         
        The Spatial Analyst Extension is required to run the tools."""

        # List of tool classes associated with this toolbox
        self.tools = [Step1, Step2, Step3]


class Step1(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Generate Kernel Density rasters"
        self.description = """The first step in the Coastal Kernel Density toolbox will model the 
        decreasing relative intensity of activity-specific stressors up to maximum impact distance
        from the source.
          
        This step will run the Kernel Density tool from the Spatial Analyst toolbox. Please enable
        the Spatial Analyst extension to run the tool: navigate to the ArcGIS Pro Licensing menu and
        select “Spatial Analyst” from the Extensions list.   
        
        The following fields will be added to the activity feature class: 
        •	Stressor Weight (prefix “StrWt_”)
        •	Stressor-specific Relative Intensity (prefix “ActRIxStrWt_”)
        •	Stressor-specific Impact Distance (prefix “ImpactDist_”)
        
        If the input activity feature class is a polygon, the tool will convert the feature class to
        polylines before running the activity feature class through the kernel density analysis. The
        tool will use the stressor-specific relative intensity field as the “population field” parameter
        and the stressor-specific or estuary-specific impact distance as the “search radius” parameter.
        
        The output from this step will be stressor-specific intermediate output rasters named with the
        scenario, activity code, associated stressor, and an impact distance. If multiple impact distances
        apply for different features or stressors, an output raster will be generated for each impact distance.
        Note:  Land-based activities represented at estuary points will have impact distances based on stream
        order and activities with multiple or different stressors per sub-activity will have impact distances 
        noted in the master stressor table.
          
        In the sample data, the raster outputs from this step are saved in the Output Workspace:
        “DFO_CI_Toolbox\CI_Coastal_Raster_Outputs.gdb”."""

        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Activity Code",
            name="act",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Input Workspace",
            name="inputworkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        param1.value = os.path.join(os.path.dirname(__file__),
                                r'CI_Coastal_Inputs.gdb\inputs')

        param2 = arcpy.Parameter(
            displayName="Output Workspace",
            name="outputWorkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        param2.value = os.path.join(os.path.dirname(__file__),
                                r'CI_Coastal_Raster_Outputs.gdb')

        param3 = arcpy.Parameter(
            displayName="Reference Grid (snap raster)",
            name="snap_raster",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        
        param3.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\pu_raster_grid_1km')

        param4 = arcpy.Parameter(
            displayName="Master Stressor Table",
            name="stressorTable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        
        param4.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\master_stressor_table')
        
        param5 = arcpy.Parameter(
            displayName = "Scenario (current/future/protected)",
            name = "scn",  
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        param5.filter.list = ["c","f","p"]

        param6 = arcpy.Parameter(
            displayName= "Intensity Attribute",
            name="strIntensity",
            datatype = "GPString",
            parameterType= "Optional",
            direction = "Input")

        
        param7 = arcpy.Parameter(
            displayName = "Impact Distance",
            name = "impactDistField",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input",
            enabled = False
        )

                
        params = [param0, param1, param2, param3, param4, param5, param6, param7] 
        return params



    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""


        #Pull the list of activities from the activity-stressor table
        activities = set()
        
        if parameters[4].valueAsText:
            rows = arcpy.da.SearchCursor(parameters[4].valueAsText,["ACTIVITY_CODE"])
            for row in rows:
                activities.add(row[0])
        if parameters[1].valueAsText and activities:
            arcpy.env.workspace = parameters[1].valueAsText
            features = arcpy.ListFeatureClasses()
            inputselection = set()
            for f in features:
                for a in activities:
                    if a in f:
                        inputselection.add(a)
            parameters[0].filter.list = list(sorted(inputselection))


        # When an activity is selected in the dropdown list identify the fields in the feature classes and
        # populate the intensity attribute dropdown list
        if parameters[5].altered:   
            activity = parameters[0].valueAsText
            scn = parameters[5].valueAsText
            arcpy.env.workspace = parameters[1].valueAsText
            features = arcpy.ListFeatureClasses(scn+"*"+activity+"*")

            
            intensityFieldList = set()
            impactDistFieldList = set()
            for feat in features:
                if activity in feat:
                    inputActivity = feat
            desc = arcpy.Describe(inputActivity)
            for field in desc.fields:
                intensityFieldList.add(field.name)
                impactDistFieldList.add(field.name)

                sorted_intensityFieldList = sorted(intensityFieldList)
                
                # populate the intensity and impact attribute field
                if "cst" in activity:
                    parameters[6].enabled = True
                    parameters[7].enabled = False
                    sorted_intensityFieldList.insert(0, "No intensity attribute present in dataset, set RI to 1")
                    parameters[6].filter.list = sorted_intensityFieldList
                if "lnd" in activity:
                    parameters[6].enabled = False
                    parameters[7].enabled = True
                    parameters[7].filter.list = sorted(impactDistFieldList)         
            
 
        ##-----------------------------------------------------------------------
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        #Check the if the activity feature class has an RI field, and if it is populated. 
        if parameters[0].valueAsText and parameters[5].valueAsText:
            act = parameters[0].valueAsText
            scn = parameters[5].valueAsText
            feature = scn+"_"+act
            try:
                rows = arcpy.da.SearchCursor(feature,"RI")
                #Glossary:
                # row[0] = Relative intensity field
                for row in rows:
                    if row[0] is None:
                        parameters[0].setWarningMessage("The RI field this activity feature class contains Null values. Please populate this field before proceeding.")
                        break
            except:
                parameters[0].setWarningMessage("This activity feature class does not have a relative intensity (RI) field. Please select an exisiting intensity field in the option below. If none of the RI options available are appropriate, please add a new intensity field.")
        return

    def execute(self, parameters, messages):
        ####"""The source code of the tool."""

        arcpy.env.overwriteOutput = True

        arcpy.management.Delete("in_memory")

        ##  Read in parameters
        act = parameters[0].valueAsText
        inputworkspace = parameters[1].valueAsText
        outputWorkspace = parameters[2].valueAsText
        snap_raster = parameters[3].valueAsText
        stressorTable = parameters[4].valueAsText
        scn = parameters[5].valueAsText
        strIntensity = parameters[6].valueAsText
        impactDist = parameters[7].valueAsText

              

        ##  Environment settings
        arcpy.env.snapRaster = snap_raster
        arcpy.env.workspace = inputworkspace
        arcpy.env.extent = snap_raster

        #create list of feature classes to determine the activity feature class using the scenario and activity code set by user

        features = arcpy.ListFeatureClasses(scn+"*"+act+"*")
        #arcpy.AddMessage(features)

        for feat in features:
            
            if act in feat:
                inputActivity = feat 
                arcpy.AddMessage("Processing "+inputActivity+"...")
            else:
                arcpy.AddError("Activity feature class not found")  #LOGIC CHECK - Selina July 18 - does the tool break on the else? should this be a try/except?
        

        ##  Create a list for stressors and Add Field parameters
        stressors = set()
        fieldparams = []

        ##  Create new cursor to iterate through table and fill set of stressors.
        rows = arcpy.da.SearchCursor(stressorTable,["STRESSOR_CODE", "ACTIVITY_CODE"])
        #region: Glossary:
        # row[0] = STRESSOR_CODE
        # row[1] = ACTIVITY_CODE
        #endregion

        ##  Fill the stressor list with stressors relevant to the input activity
        for row in rows:
            if row[1] == act:
                stressors.add(row[0])
        del rows

        #if no stressors add error detailing no stressors for that event.
        if len(stressors) == 0:
            messages.addErrorMessage("""No relevant stressors were found for the input activity. Please check the activity-stressor table to ensure that the activity code and relevant stressor codes are entered in it.
                                    Note that these codes are case-sensitive.""")
            raise arcpy.ExecuteError        


        ##Check geometry and if input data is a polygon, convert to polylines

        #create describe object of input activity in order to obtain geometry
        describe = arcpy.Describe(inputActivity)
        geometryType = describe.shapeType
        arcpy.AddMessage("Feature class geometry: " + str(geometryType))    
        
        #check geometery, if layer is polygon, transform to line.
        if geometryType =='Polygon': #check if geometry type is polygon
            
            #set name of output polyline FC
            intermedWorkspace = os.path.join(os.path.dirname(__file__),r'CI_Coastal_Inputs.gdb\Intermediates')
            activityLine=os.path.join(intermedWorkspace,os.path.basename(inputActivity)+"_Line") 
            arcpy.AddMessage("Converting polygons to polylines: "+os.path.basename(activityLine))

            #convert polygons to polylines
            arcpy.env.workspace = inputworkspace
            arcpy.management.FeatureToLine(inputActivity, activityLine)
            
            # set the activity FC used in Kernel Density tool as the line FC created above
            activity = activityLine 
        else:
            #if not polyline, then no conversion needed and can set activity FC as the input FC
            activity = inputActivity 

        
        
        #region: Weight the activity intensity by the stressor weight.
        if "lnd" not in act: #exclude land based estuary activities since they are stressor weighted in Land Index Toolbox
            arcpy.AddMessage("Calculating RI from intensity attribute...")
            # set intensity attribute, and create field in table called "RI" as needed later in tool
            arcpy.management.AddField(activity, "RI", "DOUBLE")
            
            #if user specifies that no intensity attribute is in raw data, calculate RI for all entries to 1
            if strIntensity =="No intensity attribute present in dataset, set RI to 1":
                
                arcpy.management.CalculateField(activity,"RI", 1.0, "PYTHON3")
                arcpy.AddMessage("No intensity attribute present in input dataset, RI for all entries set to 1.")
                
            else:
                arcpy.AddMessage("Setting RI to "+ str(strIntensity))
                # update cursor to apply existing intensity attribute to new RI field, or set RI to 1 if no intensity attribute present
                intensityCursor = arcpy.da.UpdateCursor(activity, [strIntensity,"RI"])
                #region Glossary: 
                # row[0] = Intensity attribute from input data
                # row[1] = relative intensity - new field called specifically "RI" for data tracing purposes.
                #endregion
                
                #check if the user defined an intensity field. If no user defined intensity then RI has already been set as 1 so no need to calculate.
                if strIntensity != "No intensity attribute present in dataset, set RI to 1":
                    for row in intensityCursor:
                        if row[0] is None:
                            arcpy.AddError("Activity " + str(activity) + " has an entry with a null value for intensity. Please check the raw data and provide an intensity, remove the null datapoint or select 'feature class has no intensity'.")
                        else:
                            row[1] = float(row[0])
                        intensityCursor.updateRow(row)
                    del intensityCursor


           #start stressor loop to perform stressor weighting for each stressor found in the feature class
            for s in stressors:
                arcpy.AddMessage("Processing stressor: "+ str(s))

                f = [("StrWt_"+s,"DOUBLE"),("RI_"+s,"DOUBLE"), ("ImpactDist_"+s, "DOUBLE")]
                fieldparams.extend(f)

                ##  Execute Add Field based on lists of parameters
                arcpy.AddMessage("Adding fields...")
                for p in fieldparams:
                    try:
                        arcpy.management.AddField(activity, p[0], p[1], "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
                        arcpy.AddMessage("Added field: " + str(p))
                    except:
                        messages.addWarningMessage(str(p) + " already exists in activity feeature class.")

                #populate stressor code field for current stressor
                arcpy.management.CalculateField(activity, "STRESSOR_CODE", "\""+str(s)+"\"", "PYTHON3")

                arcpy.AddMessage("Calculating Stressor Weight and Impact Distance...")
 
                joinFields = ["ACTIVITY_CODE", "STRESSOR_CODE","Stressor_WT", "Impact_distances"]

                #create dictionary for impact distances
                distanceDict = {}
                stressorwtDict = {}
                
                #cursor through master stressor table and fill dictionary with paired values of key (Activity, stressor, subactivity), paired to lookup value (stressor weight, impact distance)
                cursor = arcpy.da.SearchCursor(stressorTable, joinFields)
                #region: Glossary for impact distance search cursor
                # row[0] = ACTIVITY_CODE 
                # row[1] = STRESSOR_CODE
                # row[2] = the stressor weight associated with the subactivity
                # row[3] = the impact/decay distance associated with the activity
                #endregion
                for row in cursor:
                    #add paired values of (activity code, stressor code):(impact distance)
                    distanceDict.update({str(row[0])+","+str(row[1]):(row[3])})
                    stressorwtDict.update({str(row[0])+","+str(row[1]):(row[2])})
                del cursor

                #update cursor through activity table, use current row values for activity code, stressor code, subactivity as key value to look up applicable stressor weight, impact distance                      
                
                #set fields for cursor
                calcFields = ["ACTIVITY_CODE", "STRESSOR_CODE", "StrWt_"+s, "RI", "RI_"+s, "ImpactDist_"+s]
                
                arcpy.AddMessage("Calculating 'RI_"+s+"', 'Impact_Dist_"+s+"'...") 
                
                with arcpy.da.UpdateCursor(activity,calcFields) as cursor:
                    #region: Glossary for update Cursor:
                    # row[0] = ACTIVITY_CODE - code assigned unique to a human activity identifying the activity
                    # row[1] = STRESSOR_CODE - code assigned unique to an ecosystem stressor
                    # row[2] = Stressor_WT - a weighting value assigned to a subactivity to quantify differences in subactivies (i.e. paved vs unpaved roads)
                    # row[3] = RI - relative intensity of the activity within an area
                    # row[4] = RI_s - the relative intensity after being weighted by stressor
                    # row[5] = ImpactDist_s - the impact/decay distance associated with the activity
                    #endregion
                        
                    for row in cursor:
                        #assign multi-key value from current row
                        keyValue = str(row[0])+","+str(row[1]) #row[0] = ACTIVITY CODE, row[1] = STRESSOR_CODE
                        #arcpy.AddMessage(str(keyValue))                        
                        #set StrWt_s to Stressor_WT from value dictionary for current keyvalue
                        row[2] = stressorwtDict[keyValue] 
                        #Calculate stressor weighted RI (RI_s) by RI x Stressor_WT
                        row[4] = row[3]*row[2]

                        #set ImpactDist_s to Impact_distances from value dictionary for current keyValue
                        row[5] = distanceDict[keyValue]      

                        cursor.updateRow(row)
                del cursor
                
                arcpy.management.DeleteField(activity, ["STRESSOR_CODE", "Stressor_WT"])
        #endregion




        ## For each stressor, run a kernel density analysis using the correct impact distances for each stressor  
        arcpy.AddMessage("Performing Kernel Density Analysis")
        for s in stressors:
            arcpy.AddMessage("Processing stressor: "+str(s))

            #set population field to stressor weighted relative intensity, and impact distance to distance found in master stressor table
            popfield = "RI_"+s
            impactDistField = "ImpactDist_"+s

            #check to see if activity is land based (LI step 1A). if so, then set population field as "LI_s" and impact distance as the user specified impact distance
            if "lnd" in act:
                popfield = "LI_"+s
                impactDistField = impactDist

            #ensure population field is not zero as zero population would cause the KD to fail
            if popfield != 0:
                distances = set()

                #check activity for varying impact distances for same activity based on sub activity
                rows = arcpy.da.SearchCursor(activity,impactDistField)
                #glossary
                # row[0] = Impact Distance Field            
                for row in rows:
                    if row[0]:
                        distances.add(row[0])

                #for each found impact distance, perform kernel density analysis and create an output raster
                for d in sorted(distances): #looping through impact distance values that can differ due to: subactivity, stream order, etc.
                    arcpy.AddMessage(d)
                    dist = str(int(d))
                    searchradius = float(d)
                    selection = "\""+impactDistField+"\" = "+dist
                    arcpy.AddMessage(selection)
                    arcpy.management.MakeFeatureLayer(activity,"layer",selection)
                    out_kd = outputWorkspace+"\\"+scn+"_"+act+"_"+s+"_I"+dist ## scenario added - KC
                    kd = KernelDensity("layer", popfield, 100, searchradius, "SQUARE_METERS")                                       

                    kd.save(out_kd)
                    del kd
                    arcpy.management.Delete("layer")
         
        return
################################# END OF STEP 1 ###################################
    

class Step2(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Convert KD Rasters to Polygons"
        self.description = """The second step in the Coastal Kernel Density Toolbox will 
        reclassify the output rasters from Step 1, and convert them into polygons, with 
        fields containing the relative intensity of activity-specific stressors which decrease
        linearly with increasing distance from the source up to a maximum impact distance.
          
        This step will run the Slice and Reclassify Tools under the Spatial Analyst Toolbox. 
        Please ensure that you have enabled the Spatial Analyst Extension (navigate to the 
        ArcGIS Pro Licensing  menu and select “Spatial Analyst” from the Extensions list).
        
        This step will obtain a maximum value from all three scenarios of an activity and
        reclassify the kernel density raster from either
        •	0.5 to 1.5 (3 categories using Natural Breaks),
        •	or rescale it from 0 to 1 (10 equal interval bins) by dividing the raster values
            with the maximum value.
        
        If multiple stressor intensity rasters exist for a specific stressor, the relevant
        Stressor Intensity KD rasters will be added together before they are reclassified/
        rescaled and converted into polygon feature classes. 
        
        The outputs from this step are: 
        •	Stressor Intensity KD Polygons: a set of intermediate output polygons, saved in 
            output workspace, named with the activity code, the stressor, and a suffix “_KD”. 
            These output feature classes will have a new field: Stressor-specific, reclassified 
            Relative Intensity (prefix “RI_”), which will be populated with either 3 classes 
            (0.5, 1.0, 1.5) or 10 classes (0.1 to 1.0), depending on user selection.
        •	Clipped Stressor Intensity KD Polygons: a set of output polygons clipped to the
            study area, and named with the activity code, the associated, stressor, and a
            suffix “_clip”.
        """
        
        self.canRunInBackground = False

    def getParameterInfo(self):
        ##  Define parameters

        param0 = arcpy.Parameter(
            displayName="Activity Code",
            name="act",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Input Workspace",
            name="inputworkspace",
            datatype=["DEFeatureDataset","DEWorkspace"],
            parameterType="Required",
            direction="Input")
        param1.value = os.path.join(os.path.dirname(__file__),
                                r'CI_Coastal_Raster_Outputs.gdb')
        

        param2 = arcpy.Parameter(
            displayName="Output Workspace",
            name="outputWorkspace",
            datatype=["DEFeatureDataset","DEWorkspace"],
            parameterType="Required",
            direction="Input")
        param2.value = os.path.join(os.path.dirname(__file__),
                                r'CI_Coastal_Polygon_Outputs.gdb')

        param3 = arcpy.Parameter(
            displayName="Reference Grid (snap raster)",
            name="snap_raster",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        param3.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\pu_raster_grid_1km')

        param4 = arcpy.Parameter(
            displayName="Activity - Stressor Table",
            name="stressortable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        param4.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\master_stressor_table')

        param5 = arcpy.Parameter(
            displayName="Scenarios",
            name="scenarios",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue = True)
        param5.value = ["c","f","p"]

        param6 = arcpy.Parameter(
            displayName="Study Area",
            name="studyarea",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        param6.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\baselayers\studyarea')

        
        param7 = arcpy.Parameter(
            displayName="Reclass option",
            name="reclass_option",
            datatype="GPString",
            parameterType="Required",
            direction="Input")            
        param7.filter.list = ["Natural Breaks",
                              "10 equal interval bins (0.1 - 1.0)"]
        
        param8 = arcpy.Parameter(
            displayName="Number of Classes",
            name = "userClasses",
            datatype="GPSTRING",
            parameterType="Required",
            direction="Input"
        )
        param8.enabled = False
        param8.value = 3
        
        param9 = arcpy.Parameter(
            displayName="Expression for RI calculation",
            name = "expression",
            datatype="GPSTRING",
            parameterType="Optional",
            direction="Input"
        )
        param9.enabled = False
        param9.value = "!gridcode!*0.5"
        
        params = [param0,param1,param2,param3,param4,param5, param6, param7, param8, param9] 
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        activities = set()
    
        if parameters[4].valueAsText:
            rows = arcpy.da.SearchCursor(parameters[4].valueAsText,["ACTIVITY_CODE"])
            for row in rows:
                activities.add(row[0])
        if parameters[1].valueAsText and activities:
            arcpy.env.workspace = parameters[1].valueAsText
            features = arcpy.ListRasters()
            inputselection = set()
            for f in features:
                for a in activities:
                    if a in f:
                        inputselection.add(a)
            parameters[0].filter.list = list(sorted(inputselection))

        #Enable additional parameters if Natural Breaks is chosen
        if parameters[7].valueAsText == "Natural Breaks":
            parameters[8].Enabled = True
            parameters[9].Enabled = True
            parameters[9].parameterType = "Required"
            
            
        
        #Prepopulate no. of zones and expression if 10 equal interval bins is chosen        
        elif parameters[7].valueAsText == "10 equal interval bins (0.1 - 1.0)":
            parameters[8].Enabled = False
            parameters[9].Enabled = False
            parameters[8].value = 10
            parameters[9].value = "!gridcode!/10"
            

                
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        ##  Match activity code to master stressor table 

        stressortable = parameters[4].valueAsText

        ##  Check for empty output
        checktable = arcpy.management.GetCount(stressortable)
        if int(checktable.getOutput(0)) == 0:
            parameters[4].setErrorMessage("Please note that there was no value detected in the stressor weights table for that stressor / activity combination.\n"+
                                 "Please check the tables to ensure that the activity and stressor codes, are accurate and consistent, and associated"+
                                 " with valid stressors and sub-activities, or check that the value in the table is not <Null>.")
  
        #warn user to run all scenarios through step 1 before attempting step 2
        parameters[5].setWarningMessage("Please choose all applicable scenarios and ensure that all applicable scenarios have been run through step 1 of KD tools before running step 2.")
        if parameters[5].altered:
            if parameters[5].value == None:
                parameters[5].setErrorMessage("At least one scenario must be selected. Please ensure all applicable scenarios have been run through step 1 of KD tools and select all applicable scenarios")
        return

    def execute(self, parameters, messages):
        ##  The source code of the tool.

        ##  Read in parameters
        act = parameters[0].valueAsText
        inputworkspace = parameters[1].valueAsText
        outputWorkspace = parameters[2].valueAsText
        snap_raster = parameters[3].valueAsText
        stressortable = parameters[4].valueAsText
        scenarios = parameters[5].valueAsText
        studyarea = parameters[6].valueAsText
        reclass_option = parameters[7].valueAsText
        userClasses = parameters[8].value
        expression = parameters[9].valueAsText
        
        # Get path to stressor table gdb
        CEinputdata_workspace = os.path.split(stressortable)[0]
        
        ##  Environment settings
        arcpy.env.snapRaster = snap_raster
        arcpy.env.workspace = CEinputdata_workspace


        ##  Create a list for stressors and Add Field parameters, and a set for sub-activities
        stressors = set()

        ##  Create new cursor to iterate through table and fill stressor list
        rows = arcpy.da.SearchCursor(stressortable,["STRESSOR_CODE","ACTIVITY_CODE"])

        ##  Fill stressor list
        for row in rows:
            if row[1] == act:
                stressors.add(row[0].strip())


        #loop through all stressors associate with the activity class     
        arcpy.env.workspace = inputworkspace
        messages.addMessage("Identifying relevant stressors for "+act+"...")
        for s in stressors:
            arcpy.AddMessage("Processing stressor:"+s)
            rasters = []
            rastermaxvalues =[]
            reclassList = []
            
            scenario = scenarios.split(";")
            for scn in scenario:
                if scn == "c":
                    scn_str = "Current"
                elif scn == "f":
                    scn_str = "Future"
                elif scn == "p":
                    scn_str = "Protected"
                else:
                    messages.addErrorMessage("\n Please choose at least one scenario.")
                    raise arcpy.ExecuteError
                    
                
                arcpy.AddMessage("Processing "+str(scn_str) + " scenario...")
                arcpy.env.workspace = inputworkspace
                rasterList = arcpy.ListRasters(scn+"_"+act+"_"+s+"_I*")

                
                #removing a raster from the list messes with the index -
                #these multiple for loops ensure that it gets through 
                #and removes all the reclass/rescale rasters from the list 
                for raster in rasterList:
                    if 'reclass' in raster:
                        rasterList.remove(raster)
                for raster in rasterList:
                    if 'rescale' in raster:
                        rasterList.remove(raster)
                for raster in rasterList:
                    if 'cmbn' in raster:
                        rasterList.remove(raster)
                
                combined = None
                
                #check list of rasters to determine length, as different lengths have different cases
                length = len(rasterList)
                #arcpy.AddMessage(str(rasterList))
                
                messages.addMessage("Counting the no. of rasters to be processed...")
                if length == 0:
                    messages.addWarningMessage("    Please note that no '"+ str(act) +": "+ str(s) + "' rasters were found for the " + str(scn_str) + " scenario."+
                                               "\n    If you are running more than one scenario, please run Step 1 for "+
                                               "\n    all available scenarios before running Step 2 so that the RI values "+
                                               "\n    calculated will be comparable across all the scenarios.")
                                       
                    #arcpy.ExecuteError
              
                elif length == 1:
                    arcpy.AddMessage("    Found one KD raster: "+raster)
                    reclassList.append(raster)
                                    
                elif length > 1:
                    arcpy.AddMessage("    Found multiple KD rasters of varying impact distances: \n"+ str(rasterList))
                    combined = Raster(rasterList[length-1])
                    count = length -1
                    while count >= 1:
                        nextras = Raster(rasterList[count-1])
                        arcpy.env.extent = "MAXOF"
                        combined = combined + nextras
                        count = count - 1

                    if combined is not None:
                        combined.save(inputworkspace + "/"+ scn+"_"+act+"_"+s+"_cmbn")
                        reclassList.append(scn+"_"+act+"_"+s+"_cmbn")

                #arcpy.AddMessage("    Raster to be reclassified: "+ str(reclassList))    
                
                length = 0
                rasterList = []
                
                
           
                        
            arcpy.AddMessage("\nThe following rasters will be reclassified: "+str(reclassList))

            messages.addMessage("Standardizing rasters across all scenarios...")
            #Get the maximum value across rasters from all three scenarios so that RI calculated from the reclass will be comparable across scenarios.
            for r in reclassList:
                if "reclass" not in str(r):
                    maxval = float(str(arcpy.management.GetRasterProperties(r, "MAXIMUM")))
                    rastermaxvalues.append(maxval)
                    rasters.append(r)
                    #arcpy.AddMessage(r)
                    #arcpy.AddMessage(rastermaxvalues)

            maxval = max(rastermaxvalues)
            #arcpy.AddMessage(str(maxval))
            
            #Once the maxvalue has been pulled from all the scenarios, run through the reclass list again -
            #to rescale from 0-1 and reclassify via natural breaks.  
            for r in reclassList:
                scn = str(r)[0:1]
                #print(str(cf))
                
                #obtain max value across all 3 scenarios and rescale from 0-1 by dividing the raster values with max value
                constant = float(str(maxval))
                nullr = SetNull(r, r, "VALUE =0")
                rescale = Divide(nullr, constant)
                rescale.save(str(r)+"_rescale")
              
                reclass = str(r) + "__reclass"

                arcpy.env.workspace = inputworkspace
                
                messages.addMessage("Reclassifying rasters using Slice ("+reclass_option+", "+userClasses+" classes)")     
                #Reclass output rasters into RI classes (either 3 bins, or if 0-1 use 10 zones, Equal interval)
                if reclass_option == "Natural Breaks":
                    reclass = Slice(rescale, userClasses, "NATURAL_BREAKS")
                    reclass.save(str(r) + "__reclass")
                    
                elif reclass_option == "10 equal interval bins (0.1 - 1.0)":
                    reclass = Slice(rescale, userClasses, "EQUAL_INTERVAL",1)
                    reclass.save(str(r) + "__reclass")
                else:
                    messages.addErrorMessage("\n Please choose at least one reclass option.")
                    raise arcpy.ExecuteError
                     
                #Convert the reclassified rasters to KD polygons
                kd_polygon = outputWorkspace+"\\"+scn+"_"+act+"_"+s+"_KD"
                if arcpy.Exists(kd_polygon):
                    arcpy.management.Delete(kd_polygon)
                polygon = arcpy.RasterToPolygon_conversion(reclass, outputWorkspace+"\\"+scn+"_"+act+"_"+s+"_KD", "NO_SIMPLIFY","VALUE") ## scenario added - KC

                #Add stressor specific RI fields and calculate
                arcpy.management.AddField(polygon, "RI_"+s, "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

                
                #set calculate RI based on which reclassification technique was chosen
                if reclass_option == "Natural Breaks":
                    arcpy.AddMessage("Rasters were reclassified using "+userClasses+" Natural Breaks, and RI will be calculated using the following expression:")
                    arcpy.AddMessage("Expression = "+expression)
                
                elif reclass_option == "10 equal interval bins (0.1 - 1.0)":
                    # expression = "!gridcode!/10"
                    # codeblock = ""
                    arcpy.AddMessage("Rasters were reclassified using "+userClasses+" equal intervals, and RI will be calculated from 0.1 to 1.0 using the following expression:")
                    arcpy.AddMessage("Expression = "+expression)
                    
                    
                else:
                    messages.addErrorMessage("\n Please choose at least one reclass option.")
                    raise arcpy.ExecuteError
                    
                messages.addMessage("Calculating RI...")
                #calculate RI based on above expression
                arcpy.management.CalculateField(polygon, "RI_"+s, expression, "PYTHON_9.3") ## flagged for use of "RI_STRESSOR_CODE" align with other tools

                #Clip KD polygons to studyarea
                outputFC = os.path.join(outputWorkspace, scn+"_"+act+"_"+s+"_KD_clip")
                clip_polys = arcpy.analysis.Clip(polygon, studyarea, outputFC)
                
                #Add required Fields Activity and Sub_Activity
                arcpy.management.AddField(clip_polys, "ACTIVITY_CODE", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

                #Calculate fields Activity and Sub_Activity
                arcpy.management.CalculateField(clip_polys, "ACTIVITY_CODE", '"'+str(act)+'"', "PYTHON_9.3", "")
                
                #delete intermediate data
                arcpy.management.Delete(os.path.join(outputWorkspace, scn+"_"+act+"_"+s+"_KD"))
                
                arcpy.AddMessage("Output feature class: "+str(outputFC))              
            

        return


################################# END OF STEP 2 ###################################




class Step3(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3. Intersect KD polygons with the reference vector grid"
        self.description = """The third step in the Coastal Kernel Density Analysis will 
                            intersect the output polygon from Step 2 with the reference 
                            vector grid. The equivalent layer in the sample data is the
                            1km Planning Unit grid used by DFO Oceans Management for the
                            Pacific Region. The tool will create an output feature class
                            which is then used as an input dataset in Step 3 of the Marine
                            Footprint Analysis.
                            """

        self.canRunInBackground = False
        

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Activity Wildcards",
            name="act",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue = True)

        param1 = arcpy.Parameter(
            displayName="Input Workspace",
            name="inputworkspace",
            datatype=["DEFeatureDataset","DEWorkspace"],
            parameterType="Required",
            direction="Input")
        param1.value = os.path.join(os.path.dirname(__file__),
                                r'CI_Coastal_Polygon_Outputs.gdb')
 
        param2 = arcpy.Parameter(
            displayName="Output Workspace",
            name="outputWorkspace",
            datatype=["DEFeatureDataset","DEWorkspace"],
            parameterType="Required",
            direction="Input")

        param2.value = os.path.join(os.path.dirname(__file__),
                                r'CI_MarineFootprint_Outputs.gdb\Wtd_RI')

        param3 = arcpy.Parameter(
            displayName="Reference vector grid",
            name="pu_grid",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        param3.value = os.path.join(os.path.dirname(__file__),
                                    r'CI_InputData.gdb\pu_1km_Marine')

        param4 = arcpy.Parameter(
            displayName="Activity - Stressor Table",
            name="stressortable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        param4.value = os.path.join(os.path.dirname(__file__),
                                    r'CI_InputData.gdb\master_stressor_table')

        param5 = arcpy.Parameter(
            displayName="Scenarios",
            name="scenarios",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue = True)
        param5.value = ["c","f","p"]


               
        params = [param0, param1, param2, param3, param4, param5]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        activities = set()
        if not parameters[0].filter.list:
            if parameters[4].valueAsText:
                rows = arcpy.da.SearchCursor(parameters[4].valueAsText,["ACTIVITY_CODE"])
                for row in rows:
                    activities.add(row[0])
            if parameters[1].valueAsText and activities:
                arcpy.env.workspace = parameters[1].valueAsText
                features = arcpy.ListFeatureClasses("*_clip")
                inputselection = set()
                for f in features:
                    for a in activities:
                        if a in f:
                            inputselection.add(a)
                parameters[0].filter.list = list(sorted(inputselection))

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        arcpy.env.overwriteOutput = True

        arcpy.management.Delete("in_memory")
        
        # Get Parameters  
        act = parameters[0].valueAsText
        inputworkspace = parameters[1].valueAsText
        outputWorkspace = parameters[2].valueAsText
        pu_grid = parameters[3].valueAsText
        stressortable = parameters[4].valueAsText
        scenarios = parameters[5].valueAsText

        ##  Environment settings
        arcpy.env.workspace = inputworkspace
        arcpy.AddMessage("Input Workspace: "+str(inputworkspace))
        arcpy.AddMessage("Output Workspace: "+ str(outputWorkspace))

        ##  Create a set for activities and fill
        activities = set()
        scenario_set = set()
        in_features = set()
        stressors = set()
     
        ## Fill activities set
        acts = act.split(";")
        arcpy.AddMessage("Selected activities: "+str(acts))
        
        for a in acts:
            #arcpy.AddMessage(a)
            #arcpy.AddMessage("debug -- adding a:" +a)
            activities.add(a)
            #iterate through all rows and add stressor code to set if stressor is relevant to activity
            stressor_rows = arcpy.da.SearchCursor(stressortable,["ACTIVITY_CODE","STRESSOR_CODE"])
            for row in stressor_rows:                
                if row[0] == a:
                    #arcpy.AddMessage("stressor row: "+str(row))
                    stressors.add(row[1])
                else:
                    continue

            #stressor_rows.reset()
        
        #arcpy.AddMessage("Activities: "+str(activities))
        #arcpy.AddMessage("Stressors: "+str(stressors))
        
        arcpy.env.workspace = inputworkspace
        #Fill scenarios set
        # if scenarios:
        scenario_set =  set(scenarios.split(";"))
        arcpy.AddMessage("debug --- scenario_set: "+str(scenario_set))
            # scenario = scenarios.split(";")
            # for scn in scenario:
            #     scenario_set.add(scn)

        
        for scn in scenario_set:
            
            #generate list of features to be intersected with PU grid
            scnfeaturelist = arcpy.ListFeatureClasses(scn+"_*_KD_clip")
            #c_cst_logbooms_Marine_component_of_forestry_KD_clip
            if not scnfeaturelist:
                messages.addWarningMessage("No features were found in the Input Workspace for the "+str(scn)+" scenario. \n"+
                            "Please ensure that the appropriate feature classes from Step 2 have been generated for all expected scenarios.\n"+
                            "If you continue seeing this error message, try restarting ArcGIS.\n")

                continue
            arcpy.AddMessage("Processing "+str(scn)+" scenario...")

            for a in activities:
                #arcpy.AddMessage("debug --looping a: "+a)
                stressorCount = 0
                activity_stressors = set() #activity-specific stressors for handling within loop
                        
                featurelist = arcpy.ListFeatureClasses(scn+"_"+a+"_*_KD_clip")
                for f in featurelist:   
                    for s in stressors:
                        #arcpy.AddMessage("debug -- looping s: "+s)
                        if s in str(f):
                            stressorCount += 1
                            activity_stressors.add(s) 
                            arcpy.AddMessage("Processing "+str(a)+": "+str(activity_stressors))
                            arcpy.AddMessage(str(a)+ " stressor count: "+str(stressorCount))
                            
                            #set input features for intersection
                            in_features = [f, pu_grid]

                            #set name of FC to be transferred as final output of tool
                            transferName = str(scn)+"_"+str(a)+"_"+str(s)+"_WRI"
                            transferFC = os.path.join(inputworkspace,transferName)
                            
                            arcpy.AddMessage("Intersecting "+f+" with planning unit grid...")
                            #interect input feature class with PU grid to create feature class representing activity in each Marine grid cell
                            arcpy.analysis.Intersect(in_features, transferFC, "NO_FID")
                            #arcpy.AddMessage("debug -- "+str(transferFC))

                            arcpy.AddMessage("Adding and calculating fields: 'MarineAREA_"+s+"', 'PU_ID_"+s+"'")
                            #add fields for MarineAREA and PU_ID that are attached to the stressor, so that blanks can be filled in a cursor later
                            arcpy.management.AddField(transferFC, "MarineAREA_"+s, "DOUBLE")
                            arcpy.management.AddField(transferFC, "PU_ID_"+s,"DOUBLE")
                            
                            #calculate stressor specific MarineAREA and PU_ID. These are not actually stressor specific, only named as such to allow for assignment as part of stressor cleaning update cursor
                            arcpy.management.CalculateField(transferFC, "MarineAREA_"+s,"!MarineAREA!")
                            arcpy.management.CalculateField(transferFC, "PU_ID_"+s, "!PU_ID!")
                        
                            #arcpy.AddMessage("debug --- transferFC: "+transferFC)
                        else:
                            continue    
                            
                        #if stressorCount >1:
                        if len(activity_stressors) >1:
                            arcpy.AddMessage("Consolidating multiple stressors into one feature class...")
                            #create a list of created WRI feature classes
                            unionList = arcpy.ListFeatureClasses(scn+"_"+a+"_*_WRI")

                            #set name for union of all stressors associated with current activity
                            unionFCName = scn+"_"+a+"_union"
                            unionFCPath = os.path.join(inputworkspace,unionFCName)   

                            #join all WRI feature classes into one single FC using union tool
                            unionFC = arcpy.analysis.Union(unionList, unionFCPath)

                            arcpy.AddMessage("Deleting null rows...")
                            #clean union FC so that no key attributes are 0 or -1 as appropriate
                            for s in activity_stressors:
                                cleaningCursor = arcpy.da.UpdateCursor(unionFC, ["FID_"+scn+"_"+a+"_"+s+"_WRI" ,"RI_"+s,"MarineAREA", "MarineAREA_"+s,"PU_ID", "PU_ID_"+s])
                                # cleaningRow[0] = FID_scn_a_s_WRI - Stressor specific FID brought from stressor WRI FC
                                # cleaningRow[1] = RI_s - Stressor weighted relative intensity
                                # cleaningRow[2] = MarineAREA
                                # cleaningRow[3] = MarineAREA_s (used to populate MarineAREA when blanks occur)
                                # cleaningRow[4] = PU_ID
                                # cleaningRow[5] = PU_ID_s (used to populate PU_ID when blanks occur)

                                for cleaningRow in cleaningCursor:
                                    #stressor specific RI is -1 if RI is null 
                                    if cleaningRow[0] == -1:
                                        cleaningRow[1] = None
                                    if cleaningRow[3] != 0 and cleaningRow[2] == 0:
                                        #only populate MarineAREA with MarineAREA_s when MarineAREA = 0 and MarineAREA_s does not equal 0
                                        cleaningRow[2] = cleaningRow[3]
                                    if cleaningRow[5] != 0 and cleaningRow[4] == 0:
                                        #only populate PU_ID with MarineAREA_s when PU_ID = 0 and PU_ID_s does not equal 0
                                        cleaningRow[4] = cleaningRow[5]
                                    
                                    cleaningCursor.updateRow(cleaningRow)
                                del cleaningCursor
                            

                            # ensure all rows have activity code in output feature
                            arcpy.management.CalculateField(unionFC, "ACTIVITY_CODE",'"'+str(a)+'"')
                            
                            #arcpy.AddMessage("debug -- trasferFC == unionFC: "+str(unionFC))
                            #set transferFC to unionFC since there are multiple FCs to transfer
                            transferFC = unionFC
                    
                        #after data is cleaned, copy features to new final output FC carrying only relevant attributes
                        #build list of fields to copy
                        fieldList = ["PU_ID", "MarineAREA", "ACTIVITY_CODE"]
                        for s in activity_stressors:
                            #arcpy.AddMessage("debug -- "+a+": RI_"+s)
                            fieldList.append("RI_"+s)


                        #create field mappings object to collect field maps
                        fm = arcpy.FieldMappings()
                        
                        #for each field found in the fieldlist, create a new field map and add to the field mappings object
                        for field in fieldList:
                            #arcpy.AddMessage("debug -- input field: "+str(field))
                            fieldmap = arcpy.FieldMap()
                            fieldmap.addInputField(transferFC, field)
                            fm.addFieldMap(fieldmap)
                        
                        ##debug print fieldmap
                        #arcpy.AddMessage("fieldmaps-- " +str(fm))

                        #copy FC to new FC in output Database
                        finalOutputFCName = scn + "_" + a + "_WRI"
                        arcpy.conversion.FeatureClassToFeatureClass(transferFC, outputWorkspace, finalOutputFCName,"", fm)
                        arcpy.AddMessage("Output feature class: "+(os.path.join(outputWorkspace, finalOutputFCName)))
                    
        return

################################# END OF STEP 3 ###################################