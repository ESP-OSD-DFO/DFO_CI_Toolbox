#developed using ArcGIS Pro, versions up to and including v 2.8.8 and 
# Python version 3.1 (check in folder)
import arcpy, os, sys
from arcpy.sa import *



class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Marine Footprint Toolbox"
        self.alias = "MarineFootprint"
        self.description = """The Marine Footprint analysis calculates the 
            cumulative impact from activities that have an impact over a 
            specific area and are represented by polygon spatial data.
         
            Data for all activities and habitats must go through Marine Footprint
            Steps 3-5 to be included in the cumulative impact score. Outputs from
            the Land Index and Coastal Kernel Density Toolboxes are used as inputs 
            in Step 3 of the Marine Footprint Toolbox. 
            
            Calculating Impact Scores: 
            Step 1 calculates the relative intensity (RI), and Step 2 calculates 
            the stressor weighted RI (Wtd_RI) which will be used in Step 3 to
            calculated area weighted impact scores. Outputs from the Land Index and
            Coastal Kernel Density Toolboxes are converted into polygons representing 
            the footprint of the impact of coastal and land activities on the marine.
            Therefore, these outputs are inserted into the Marine Footprint toolbox 
            at Step 3. 
            
            Calculating Cumulative Impact Scores:
            Step 4 calculates sum impact scores per activity across all habitats. 
            Step 5 is run in two parts. Part 1 calculates sum impact scores across 
            activities per habitat, and Part 2 calculates cumulative impact scores 
            across all activities and all habitats.
             
            To calculate cumulative impact scores for sectors (i.e., a subset of activities
            such as fishing or coastal), Step 5 can be run for a subset of activities which
            are identified with a unique sector descriptor to identify sector specific output 
            geodatabases and prefixes to identify sector specific output tables."""

        # List of tool classes associated with this toolbox
        self.tools = [Step1,Step2,Step3,Step4,Step5,Step6]
        


class Step1(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Calculate Relative Intensity (RI)"
        self.description = """The first step of the Marine footprint analysis is calculating a relative intensity (RI) value. 
        Relative intensities are a quantification of the amount of activity occurring within each planning unit in the study
        area relative to the rest of the study area. 

        In order to run the cumulative effects analysis, the intensity (e.g., effort hours, frequency of occurrence) of each
        activity must be standardized across all scenarios. 
        
        The following options are provided: 
        •	Rescale from 0-1: all values will be divided by the max value in the dataset to produce a continuous classification 
            from 0-1.
        •	Reclassify using Natural Breaks: values will be reclassified using the natural breaks method using a user-specified 
            no. of classes and a reclass expression to further modify the output classes. If this option is selected, The default
            value for no. of classes is 3, and the default reclass expression is "!RI_reclass!*0.5" to convert the classes to 0.5,
            1.0, and 1.5.
        •	Do not rescale: Please use this option if the data has been pre-processed and there is a pre-determined RI field available.
            Please ensure that your RI values are relative across all scenarios you plan to run.
        
        Important notes: 
        •   If the data needs to be log transformed before rescaling, the log transformation needs to be applied before the data is 
            run through this step.
        •   If you are planning on running multiple scenarios for your analysis, please ensure that data for all relevant scenarios 
            have been run through the appropriate Data Preparation toolbox steps. """
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Activity Code",
            name="activity",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
       
        param1 = arcpy.Parameter(
            displayName = "Input Workspace",
            name = "inputWorkspace",
            datatype = ["DEWorkspace", "DEFeatureDataset"],
            parameterType = "Required",
            direction = "Input")
        param1.value = os.path.join(os.path.dirname(__file__),
                                r'CI_MarineFootprint_Inputs.gdb\inputs')

        param2 = arcpy.Parameter(
            displayName="Output Workspace",
            name="outputWorkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")
        param2.value = os.path.join(os.path.dirname(__file__),
                                r'CI_MarineFootprint_Outputs.gdb\RI')

        param3 = arcpy.Parameter(
            displayName="Reference Grid (vector)",
            name="vector_grid",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")
        param3.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\baselayers\pu_1km_Marine')

        param4 = arcpy.Parameter(
            displayName="Intensity Attribute",
            name="intensity_attr",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param4.enabled = False
        
        param5 = arcpy.Parameter(
            displayName="Rescale Option",
            name="rescale_option",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue = False)
        param5.filter.type = "ValueList"
        param5.filter.list = ["Rescale from 0 to 1",
                              "Reclassify using Natural Breaks",
                              "Do not rescale"]

        param6 = arcpy.Parameter(
            displayName="Activity/Stressor Table",
            name="stressortable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        #param6.value = r"C:\DFO_CI_Toolbox\CI_InputData.gdb\master_stressor_table"
        param6.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\master_stressor_table')        

        #Add parameters for: user defined min, user defined max, user defined number of classes, user defined expression for recalc RI (ours uses reclass RI * 0.5)

        param7 = arcpy.Parameter(
            displayName="Number of Classes",
            name = "classCount",
            datatype = "GPLong",
            parameterType = "Optional",
            direction = "Input")
        param7.enabled = False
        param7.value = 3

        param8 = arcpy.Parameter(
            displayName = "Reclass expression",
            name = "userExpression",
            datatype= "GPString",
            parameterType = "Optional",
            direction = "Input")
        param8.enabled = False
        param8.value = "!RI_reclass!*0.5"
        
        param9 = arcpy.Parameter(
            displayName="Scenarios",
            name="scenarios",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue = True)
        param9.value = ["c","f","p"]
        
        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[5].altered:
                
            if parameters[5].valueAsText =="Reclassify using Natural Breaks":
                parameters[7].enabled = True
                parameters[8].enabled = True
            else:
                parameters[7].enabled = False
                parameters[8].enabled = False

        # Determine which set of activties are included in the features to be processed
        # then populate the dropdown list with activity codes
        activities = set()
        if not parameters[0].filter.list:  #if activity dropdown list is empty
            if parameters[6].valueAsText:  
                rows = arcpy.da.SearchCursor(parameters[6].valueAsText,["ACTIVITY_CODE"])
                for row in rows:
                    activities.add(row[0])
                del rows
            if parameters[1].valueAsText and activities:
                arcpy.env.workspace = parameters[1].valueAsText
                features = arcpy.ListFeatureClasses()
                inputselection = set()
                for f in features:
                    for a in activities:
                        if a in f:
                            inputselection.add(a)
                #populate dropdown list with activities
                parameters[0].filter.list = list(sorted(inputselection))

        # When an activity is selected in the dropdown list identify the fields in the feature classes and
        # populate the intensity attribute dropdown list
        if parameters[0].altered:   
            activity = parameters[0].valueAsText
            arcpy.env.workspace = parameters[1].valueAsText
            features = arcpy.ListFeatureClasses("*"+activity+"*")
            fieldlist = set()
            for feat in features:
                fields = arcpy.ListFields(feat)
                for f in fields:
                    fieldlist.add(f.name)
            # populate the intensity attribute field
            parameters[4].enabled = True        
            parameters[4].filter.list = list(sorted(fieldlist))

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        ## Clear cache
        arcpy.management.Delete("in_memory")

        ## Assign parameters to variables (Note index starts at 0)
        
        activity = parameters[0].valueAsText
        inputWorkspace = parameters[1].valueAsText
        outputWorkspace = parameters[2].valueAsText
        vector_grid = parameters[3].valueAsText
        intensity_attr = parameters[4].valueAsText
        rescale_option = parameters[5].valueAsText
        classCount = parameters[7].value
        userExpression = parameters[8].valueAsText
        scenarios = parameters[9].valueAsText
        
        
        #set workspace
        arcpy.env.workspace = inputWorkspace
        
        #iterate through scenarios looking for inputs matching that scenario and activity 
        scenario_list = scenarios.split(";")       
        for scn in scenario_list:
            if scn == "c":
                scn_str = "Current"
            elif scn == "f":
                scn_str = "Future"
            elif scn == "p":
                scn_str = "Protected"
            else:
                messages.addErrorMessage("\n Please choose at least one scenario.")
                raise arcpy.ExecuteError
            
            #List all feature classes for the scenario and activity combination
            features = arcpy.ListFeatureClasses(scn+"_"+activity)
            if not features:
                messages.addWarningMessage("No features were found in the Input Workspace for the "+scn_str+" scenario. \n"+
                        "Please ensure that the appropriate feature classes from the Data Preparation toolbox have been generated for all expected scenarios.\n"+
                        "If you continue seeing this error message, try restarting ArcGIS.\n")
                continue
            
            for feature in features:
                arcpy.AddMessage("Processing "+scn_str+" scenario...")                
                arcpy.AddMessage("Intersecting "+ str(feature)+" with planning unit grid...")
                activity_fc = feature
                intersect_grid = arcpy.analysis.Intersect([activity_fc, vector_grid],str(inputWorkspace)+'\intgrid')
                # intersect_grid = arcpy.analysis.PairwiseIntersect([activity_fc, vector_grid],str(inputWorkspace)+'\intgrid')
                arcpy.env.workspace = outputWorkspace
                RI = scn+"_"+activity+"_RI"
                
                if arcpy.Exists(RI):
                    arcpy.management.Delete(RI)
                    arcpy.AddMessage("Overwriting exisiting RI feature class...")

                arcpy.AddMessage("RI feature class: "+str(RI))    

                if rescale_option == "Do not rescale":
                    #dissolve by UNIT ID and intensity attribute to keep the scale set by the user
                    arcpy.management.Dissolve(intersect_grid,RI, ["ACTIVITY_CODE", "Sub_Activity", "UNIT_ID", "MarineAREA", "Stressor_WT", intensity_attr]," ","MULTI_PART","DISSOLVE_LINES")
                    arcpy.AddMessage("Do not rescale option selected: features dissolved by UNIT_ID, intensity attribute not summarized. ")

                if rescale_option == "Rescale from 0 to 1" or rescale_option == "Reclassify using Natural Breaks":
                    #add SUM intensity attribute per Unit ID before scaling from 0-1
                    arcpy.management.Dissolve(intersect_grid,RI, ["ACTIVITY_CODE", "Sub_Activity", "UNIT_ID", "MarineAREA","Stressor_WT"], intensity_attr+" SUM","MULTI_PART", "DISSOLVE_LINES")
                    intensity_attr = "SUM_"+intensity_attr
                    arcpy.AddMessage("Rescale/reclass option selected: features dissolved and intensity attribute summarized by UNIT_ID."+
                                     "\nIntensity attribute used: "+str(intensity_attr))
                
                #delete temporary intersection FC as it is no longer needed
                arcpy.management.Delete(intersect_grid)
            
            #reset workspace to input for the next loop iteration    
            arcpy.env.workspace = inputWorkspace
        
        #Transform values: rescale from 0-1 or reclassify into 3 bins 
        arcpy.AddMessage("Standardizing intensity across all relevant scenarios...")
        # #set intensity attribute to the sum intensity calculated during dissolve step above. 
        # #If no rescale called for, intensity attribute is not summed, and remains the same as user input.
        # if rescale_option == "Rescale from 0 to 1" or rescale_option == "Reclassify using Natural Breaks":
        #     intensity_attr = "SUM_"+intensity_attr

        #set workspace to output workspace
        arcpy.env.workspace = outputWorkspace
        #generate list of features containing the activity code
        features = arcpy.ListFeatureClasses("*_"+activity+"_RI")
        for feature in features:
            arcpy.AddMessage("Processing "+str(feature)+"...")
            
            #Add Field RI if not present
            fieldList = arcpy.ListFields(feature,"RI")
            if len(fieldList)==0:
                arcpy.management.AddField(feature, "RI", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
                arcpy.AddMessage("Adding RI field...")

            
            #If the user has already set their RI scale and does not want to transform the data,
            #copy instensity attribute directly into RI field
            if rescale_option == "Do not rescale":
                arcpy.management.CalculateField(feature, "RI", "!"+str(intensity_attr)+"!", "PYTHON3")
                arcpy.AddMessage("Do not rescale option selected: values from "+str(intensity_attr)+" copied to RI field.")
                continue
                
            
            #make a set for storing max value for each scenario processed
            arcpy.AddMessage("Determining max intensity value across all scenarios...")
            maxValues = set()
            outTableName = scn+"_"+activity+"_statistics"
            tempWorkspace = os.path.join(os.path.dirname(__file__),r'CI_MarineFootprint_Outputs.gdb')
            outTable = os.path.join(tempWorkspace,outTableName)
            maxTable = arcpy.analysis.Statistics(feature, outTable, [[intensity_attr, "MAX"]])
            maxCursor = arcpy.da.SearchCursor(maxTable, "MAX_"+intensity_attr)
            
            for row in maxCursor:
                maxValues.add(int(row[0]))

            #delete statistics table as no longer useful
            arcpy.management.Delete(maxTable)

        if rescale_option != "Do not rescale":
            #Determine maximum value within list of scenario maximums
            maxValue = max(maxValues)


            arcpy.AddMessage("Calculating standardized RI for all relevant scenarios...")
            
            for scn in scenario_list:
                for feature in features:
                    if feature[:1] == scn:
                        arcpy.AddMessage("Processing "+feature+"...")
                        #for each feature class, standardize RI across all scenarios by dividing RI by the maximum RI value of all scenarios
                        arcpy.management.CalculateField(feature, "RI","!"+intensity_attr+"!/"+str(maxValue))

                        if rescale_option == "Reclassify using Natural Breaks":
                            arcpy.AddMessage("Reclassifying RI to Natural Breaks...")
                            arcpy.management.ReclassifyField(feature, str(intensity_attr), "NATURAL_BREAKS", classCount, None, "ONE", None, "ASC", "RI_reclass")
                            arcpy.management.CalculateField(feature, "RI", userExpression, "PYTHON3", '', "TEXT")
                    else:
                        continue
        
        arcpy.AddMessage("Output feature classes: "+str(features))    
       
        return


#######################################     End Step 1     ##################################



class Step2(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Calculate Weighted Relative Intensity (Wtd_RI)"
        self.description = """This step takes the RI feature class created in Step 1 and applies stressor 
        weights to the relative intensity of the activity based on subactivities. Stressor weights are 
        relative intensity weights (e.g., “stressor weights”) that will be applied to sub-activities
        within each activity-stressor combination. Stressor weights are applied when stressors are known to
        behave differently between sub-activities, but stressor-specific relative intensity data is not available. 
        
        If there are no subactivities for an activity, the stressor weight applied will be 1. 
        The output feature class from this step is the weighted relative intensity (Wtd_RI).  """
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName = "Input Workspace",
            name = "inputWorkspace",
            datatype = ["DEWorkspace", "DEFeatureDataset"],
            parameterType = "Required",
            direction = "Input")
        param0.value = os.path.join(os.path.dirname(__file__),
                                r'CI_MarineFootprint_Outputs.gdb\RI')  
        
        param1 = arcpy.Parameter(
            displayName="Relative Intensity (RI) Feature Class ",
            name="RI_fc",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Scenario (current/future/protected)",
            name="scn",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2.filter.list = ["c","f","p"]

        param3 = arcpy.Parameter(
            displayName="Output Workspace",
            name="outputWorkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")
        param3.value = os.path.join(os.path.dirname(__file__),
                                r'CI_MarineFootprint_Outputs.gdb\Wtd_RI')
        
        param4 = arcpy.Parameter(
            displayName="Master Stressor Table",
            name="stressortable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        param4.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\master_stressor_table')

        params = [param0, param1, param2, param3, param4]
        
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[0].value:
            inputWorkspace =  parameters[0].valueAsText
            arcpy.env.workspace = inputWorkspace
            fcList = arcpy.ListFeatureClasses("*")
            parameters[1].filter.list = fcList
        
        
        ## The feature classes are named according to the scenario naming 
        ## convention, where the scenario is identified by a letter c/f at the beginning
        ## of the filename. Here, the script identifies the scenario and automatically
        ## fills in the scenario variable for the user. The scn variable is used to name
        ## the output feature classes.
        if parameters[1].value:
            RI_fc = parameters[1].valueAsText
            parameters[2].value = RI_fc[:1]

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        ##  Check for empty stressor table output
        if parameters[4].valueAsText:
            checktable = arcpy.management.GetCount(parameters[4].valueAsText)
            
            if int(checktable.getOutput(0)) == 0:
                parameters[5].setErrorMessage("Unable to retrieve any stressors from the Activity Stressor Table.\n"+
                                    "Please check the table and feature class to ensure that the activity codes are accurate and associated"+
                                    " with valid stressors.")        
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        arcpy.management.Delete("in_memory")
        inputWorkspace = parameters[0].valueAsText
        RI_fc = parameters[1].valueAsText
        scn = parameters[2].valueAsText
        outputWorkspace = parameters[3].valueAsText
        stressortable = parameters[4].valueAsText
        
        arcpy.env.workspace = outputWorkspace

#2.0.4

        #RI_fc = full path to feature class
        RI_feature = os.path.join(inputWorkspace, RI_fc)

        arcpy.AddMessage("Processing "+str(RI_feature)+"...")
        ##  Pull the activity code from the Activity field of the activity feature class
        ##  This code is used to name the output feature classes
        try:
            act = ""
            with arcpy.da.UpdateCursor(RI_feature, ["ACTIVITY_CODE","Sub_Activity"]) as rows:
                for row in rows:
                    act = row[0]
                    #store subactivity from field as string
                    subAct = str(row[1])
                    #convert string to all caps to encompass all possible variations of "none". if "NONE" is found, set subactivity to "None" as used in master stressor table
                    if subAct.upper() == "NONE":
                        row[1] = "None"
                    rows.updateRow(row)
            del rows
        except:
            messages.addErrorMessage("Cannot find the following fields in the activity feature class: "+
                                        "\n\nACTIVITY_CODE\nSub_Activity")
            raise arcpy.ExecuteError

        #check for existing WRI FC and delete if it exists
        WRI = scn+"_"+act+"_RI"    
        if arcpy.Exists(WRI):
            arcpy.management.Delete(WRI)
            arcpy.AddMessage("Overwriting exisiting WRI feature class...")


        ##  Create a stressor list. Use SearchCursor to iterate through stressor_table table view, and limit list to stressors associated with the activity
        ##  populate the stressor list
        stressors = set()
        rows = arcpy.da.SearchCursor(stressortable,["STRESSOR_CODE","ACTIVITY_CODE"])
        # row[0] = STRESSOR_CODE
        # row[1] = ACTIVITY_CODE
        for row in rows:
            if row[1] == act:
                stressors.add(row[0].strip())
        del rows

        #Create output feature class (Weighted index)
        arcpy.env.workspace = outputWorkspace
        wtd_RI = arcpy.management.CopyFeatures(RI_feature, scn+"_"+act+"_WRI")
        
        arcpy.AddMessage("Adding fields...")
        
        fieldparams =[]
        for s in stressors:
            arcpy.AddMessage("Processing "+s+"...")
            f = [("RI_"+s,"DOUBLE"),("STRESSOR_CODE","TEXT") ]
            fieldparams.extend(f)
            
            for p in fieldparams:
                arcpy.management.AddField(wtd_RI, p[0], p[1], "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
                
            arcpy.management.CalculateField(wtd_RI, "STRESSOR_CODE", "\""+str(s)+"\"", "PYTHON3")

            
            #declare list of fields of interest to restrict cursors. restriction reduces processing time.
            joinFields = ["Stressor_WT", "RI", "RI_"+s]

            #use update cursor to apply stressor weight value from master stressor table to weighted relative intensity feature class table.
            updCursor= arcpy.da.UpdateCursor(wtd_RI,joinFields)
            #row[0] = Stressor_WT - Stressor weight associated with activity. referenced from master stressor table
            #row[1] = RI - relative intensity 
            #row[2] = RI_s - stressor weighted relative intensity
            for record in updCursor:
                record[2] = float(record[0])*record[1]
                updCursor.updateRow(record)
            del updCursor

            #delete stressor code field so that nest iteration can have the stressor code applied
            arcpy.management.DeleteField(wtd_RI, "Stressor_CODE")
        
        arcpy.AddMessage("Output feature class: "+str(wtd_RI))

        arcpy.ResetEnvironments()      
        
        return

 ########################################################################################################


class Step3(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3. Calculate Area-Weighted Impact Scores"
        self.description = """ This step calculates the impact scores based on the area weighted RI calculated 
        in the previous step. The input feature class will be intersected with habitat feature classes, and the 
        weighted RI values will be multiplied by the appropriate vulnerability (and fishing gear severity scores 
        where appropriate) to generate a habitat area weighted impact score. """
        self.canRunInBackground = False

    def getParameterInfo(self):
        ##  Define parameters
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName = "Input Workspace",
            name = "inputWorkspace",
            datatype = ["DEWorkspace", "DEFeatureDataset"],
            parameterType = "Required",
            direction = "Input")
        param0.value = os.path.join(os.path.dirname(__file__),
                                r'CI_MarineFootprint_Outputs.gdb\Wtd_RI')  

        param1 = arcpy.Parameter(
            displayName="Weighted Relative Intensity (RI) Feature Class",
            name="WtdRI_fc",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Vulnerability Score Table",
            name="vscoretable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        param2.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\vscores_habitats')

        param3 = arcpy.Parameter(
            displayName="Master Stressor Table",
            name="stressortable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        param3.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\master_stressor_table')

        param4 = arcpy.Parameter(
            displayName = "Fishing Gear Severity Table",
            name = "fishing_severity",
            datatype = "DETable",
            parameterType = "Required",
            direction = "Input")
        param4.value = os.path.join(os.path.dirname(__file__),
                                r'CI_InputData.gdb\fishing_severity')

        param5 = arcpy.Parameter(
            displayName = "Habitat Workspace",
            name = "habWorkspace",
            datatype = ["DEFeatureDataset", "DEWorkspace"],
            parameterType = "Required",
            direction = "Input",
            )
        param5.value = os.path.join(os.path.dirname(__file__), r'CI_InputData.gdb\habitats')

        param6 = arcpy.Parameter(
            displayName="Habitat feature classes",
            name="habitatFCs",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue = True)

        param7 = arcpy.Parameter(
            displayName="Output Workspace",
            name="outputWorkspace",
            datatype="DEFeatureDataset",
            parameterType="Required",
            direction="Input")
        
        param7.value = os.path.join(os.path.dirname(__file__),
                                r'CI_MarineFootprint_Outputs.gdb\Impact')                             
                                
        param8 = arcpy.Parameter(
            displayName="Scenario",
            name="scn",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param8.filter.list = ["c","f","p"]
        
        param9 = arcpy.Parameter(
            displayName="Run Pairwise Intersect",
            name="pairwise",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param9.value = True

       
        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9]
        return params


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[0].value:
            inputWorkspace =  parameters[0].valueAsText
            arcpy.env.workspace = inputWorkspace
            fcList = arcpy.ListFeatureClasses("*")
            parameters[1].filter.list = fcList
        
        # Autofill "Current or Future" dropdown menu based on first letter of Wtd_RI Feature Class
        feature = parameters[1].valueAsText
        if feature:
            WtdRI_fc = os.path.basename(feature)
            parameters[8].value = WtdRI_fc[:1]
 
        if parameters[5]:
            #set workspace to habitat workspace and list feature classes in workspace
            arcpy.env.workspace = parameters[5].value
            habList = []
            fcList = arcpy.ListFeatureClasses()
            for fc in fcList:
                habList.append(os.path.basename(fc))
            parameters[6].filter.list = sorted(habList)
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
        ## Added by Michael She - May 2016
        ## Shows a warning message when habitat layers are selected reminding users to check that all the layers that they have selected are represented in the VScore Table.
        if parameters[5].value and parameters[2].value:
            parameters[5].setWarningMessage("Please make sure that the habitat feature classes entered here match the VScore table.")
            parameters[2].setWarningMessage("Please make sure that the VScore table entered here matches the habitat feature classes selected below.")

        return


    def execute(self, parameters, messages):
        ##  The source code of the tool.

        ##  Read in parameters
        inputWorkspace = parameters[0].valueAsText
        WtdRI_fc = parameters[1].valueAsText
        vscoretable = parameters[2].valueAsText
        stressortable = parameters[3].valueAsText
        fishing_severity = parameters[4].valueAsText
        habitatWorkspace = parameters[5].valueAsText
        habitatFCs = parameters[6].valueAsText
        outputWorkspace = parameters[7].valueAsText
        scn = parameters[8].valueAsText
        pairwise = parameters[9].value 
        
         #clear cache
        arcpy.management.Delete("in_memory")
        
        ##  Environment settings
        #inputWorkspace = os.path.split(WtdRI_fc)[0]
        arcpy.AddMessage("Input Workspace: "+str(inputWorkspace))
        arcpy.env.workspace = inputWorkspace

        ##  Grab the activity code from the input feature
        act = ""
        with arcpy.da.UpdateCursor(WtdRI_fc,"ACTIVITY_CODE") as rows:
            #loop through rows, and grab the first activity and break loop (all rows will have same activity for one FC)
            for row in rows:
                act = row[0]
                break
        del rows

         #check if field "Shape_Area" exists if not add and calculate one
        fieldList = arcpy.ListFields(WtdRI_fc)
        
        shapeExists = False

        for field in fieldList:
            if field.name.upper() == "SHAPE_AREA":
                shapeExists = True

        if shapeExists == False:
            # add a field and calculate geometry, standardize geometry variable so that it is the same for all data sources.
            arcpy.management.AddField(WtdRI_fc, "Shape_Area","DOUBLE")
            arcpy.management.CalculateGeometryAttributes(WtdRI_fc, [["Shape_Area","AREA"]], area_unit ="SQUARE_METERS")
        
        # pull list of unique stressors from the master_stressor_table restricted to those that "belong" to the activity grabbed above
        expression = "\"ACTIVITY_CODE\" = '" + act + "'"
        with arcpy.da.SearchCursor(stressortable, "STRESSOR_CODE",expression) as cursor:
            stressors = sorted({row[0] for row in cursor})
        del cursor

        #create lists to collect feature class and habitat combinations that did not have an associated fishing gear score, vulnerability score or impact score. Must be here as they have to be created once for all habitats not one for each
        noFishingList = []
        NoVScoreList = []

        # populate list of habitats
        habitats = habitatFCs.split(";")
        
        #for hf in habitat_features:
        for hab in habitats:
            hf = os.path.join(habitatWorkspace,hab)
            arcpy.AddMessage("Processing habitat: "+hab)

            # pull list of unique HabitatCODEs from attributes of habitat feature classes 
            with arcpy.da.SearchCursor(hf, ["HabitatCODE"]) as cursor:
                HabitatCODE = sorted({row[0] for row in cursor})
            del cursor
            if not HabitatCODE:
                arcpy.AddError("Unable to match files with a habitat. The filenames of the Habitat feature classes may be incorrect.\n"+
                                         "Feature class names are case sensitive 2-letter codes:\n"+
                                         "\"benthic habitats = bh\"\n"+
                                         "\"deep pelagic habitats = dp\"\n"+
                                         "\"eelgrass habitats = eg\"\n"+
                                         "\"kelp habitats = kp\"\n"+
                                         "\"shallow pelagic habitats = sp\"\n"+
                                         "\"sponge reef habitats = sr")
                return

            arcpy.AddMessage("Habitat codes: "+str(HabitatCODE))
            
            #Create Dictionaries to transfer vulnerability scores and fishing gear severity scores from master tables to output FCs

            arcpy.env.workspace = inputWorkspace

            #populate a dictionary of VSCORES with all possible combinations of Activity Code, Stressor Code and associated habitat codes
            #vscoreRow[0] = ACTIVITY_CODE
            #vscoreRow[1] = STRESSOR_CODE
            #vscoreRow[2] = HabitatCODE
            #vscoreRow[3] = VSCORE
           
            vscoreDict = {}
            vscoreFields = ["ACTIVITY_CODE","STRESSOR_CODE","HabitatCODE", "VSCORE"]
            vscoreCursor = arcpy.da.SearchCursor(vscoretable, vscoreFields)
            for vRow in vscoreCursor:
                #create a new dictionary entry for each unique activity, stressor, and habitat code multikey to the vscore
                vscoreDict.update({str(vRow[0])+","+str(vRow[1])+","+str(vRow[2]):vRow[3]})
            del vscoreCursor

            #populate a dictionary of fishing severity with all possible combinations of Activity code, stressor code, and gear type severity scores
            #fishRow[0] = ACTIVITY_CODE
            #fishRow[1] = STRESSOR_CODE
            #fishRow[2] = Gear_Type_Severity_Score
            fishFields = ["ACTIVITY_CODE", "STRESSOR_CODE","Gear_Type_Severity_Score"]
            fishingCursor = arcpy.da.SearchCursor(fishing_severity, fishFields)
            fishingDict = {}
            for fishRow in fishingCursor:
                #create a new dictionary entry for each unique activity and stressor multikey to the fishing gear severity.
                fishingDict.update({str(fishRow[0])+","+str(fishRow[1]):fishRow[2]})
            del fishingCursor


            feat = os.path.join(os.path.dirname(__file__),r"CE_Marine_Footprint_Outputs.gdb\WRI", scn+"_"+act+"_WRI")

            featuresall = arcpy.ListFeatureClasses(scn+"_"+act+"*_WRI") ## scenario added - KC


            for feat in featuresall:
                arcpy.AddMessage("Processing "+str(feat))
                ##  Intersect activity polygons with habitat polygons
                for s in stressors:  #stressor isn't carried by the activity class so must loop through all stressors (restricted to those relevant to the activity as above)

                    for code in HabitatCODE:
                        arcpy.AddMessage("Processing: " + str(code))    

                        #for each habitat code, create a layer, select only features from the habitat layer that have that code
                        arcpy.management.MakeFeatureLayer(hf, "habitat_features_lyr")
                        arcpy.management.SelectLayerByAttribute("habitat_features_lyr", "NEW_SELECTION", "HabitatCODE = '"+code+"'")
                        arcpy.management.CopyFeatures("habitat_features_lyr", code+"_temp")
                                                
                        
                        #set the output file name
                        outputfile = scn+"_"+act+"_"+s+"_"+hab+"_"+code
                        arcpy.AddMessage("Output: "+str(outputfile))
                
                        #set the output file path. 
                        outputfc = os.path.join(outputWorkspace,outputfile)
                        
                        #check if there is already an FC in the output GDB called  if it already exists, then delete existing table before creating new intersection
                        if arcpy.Exists(outputfc):
                            arcpy.management.Delete(outputfc)
                            
                        #specify layers to be intersected
                        intersectparams = [feat,code+"_temp"]
                        #pairwise intersect to take advantage of parallel processing
                        if pairwise == True:
                            intersection = arcpy.analysis.PairwiseIntersect(intersectparams, outputfc) ## scenario added - KC
                        else:
                            intersection = arcpy.analysis.Intersect(intersectparams, outputfc) ## scenario added - KC
                        
                        # if activity does not occur in habitat, delete outputfc and continue to other habitats
                        #temporary code layer is not needed for further steps, delete
                        arcpy.management.Delete(code+"_temp")

                        #count number of records in the table 
                        result = arcpy.management.GetCount(outputfc)
                        
                        count = int(result.getOutput(0))
                        arcpy.AddMessage("        counting features: "+str(count))

                        #if no records in the intersection then there is no interaction between activity and habitat, and the new FC can be deleted as it will have all 0 results
                        if count == 0:
                            arcpy.AddMessage("        deleting: "+str(outputfc))
                            arcpy.management.Delete(outputfc)
                        else:
    #3.1.6
                            ##  Add needed fields for impact calculation 
                            fieldparams = [("Vscore_"+hab+"_"+s, "DOUBLE"), ("Impact_"+hab+"_"+s, "DOUBLE"), ("ADJ_HabAREA_WT", "DOUBLE"), ("Wtd_Impact", "DOUBLE")]
                            
                            #check to see if activity is fishing related, if it is then add an attribute for fishing gear score
                            if "cf" in act or "sportf" in act:
                                fishGearFieldName = "fishgear_score_"+act
                                #for data tracing purposes, add fishing gear field after Vscore field
                                fieldparams.insert(1,(fishGearFieldName, "DOUBLE"))
                                  
                            #iterate through field parameters list to add parameters to intersect FC
                            for p in fieldparams:
                                arcpy.management.AddField(intersection, p[0], p[1], "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
                                #arcpy.AddMessage("        Adding fields: "+str(p))
    #3.1.7
                            ##  Populate Vscore field
                            arcpy.AddMessage("Populating vulnerability scores...")
                            #create update cursor to update table row by row
                            intersection_rows = arcpy.UpdateCursor(intersection)
                            for int_row in intersection_rows:
                                a = str(int_row.getValue("ACTIVITY_CODE"))        
                                #check if habitat is land or none, which do not use this analysis
                                h = int_row.getValue("HabitatCODE")
                                if h == "LAND" or h is None:
                                    arcpy.AddMessage("          Vscore_hab for: "+str(h)+ "== <Null>")
                                else:
                                    #for each row in intersect table, set the keyvalue to search dictionaries for associated vscore/fishing gear score
                                    vscoreKeyValue = str(a)+","+str(s)+","+str(h)
                                    fishKeyValue = str(a)+","+str(s)
                                    #when vscore key is found, apply associate vscore to vscore attribute of intersect table
                                    if vscoreKeyValue in vscoreDict:
                                        int_row.setValue("Vscore_"+hab+"_"+s,vscoreDict[vscoreKeyValue])
                                        # arcpy.AddMessage(str(vscoreKeyValue))
                                        # arcpy.AddMessage(str(vscoreKeyValue) + " has a vscore of " + str(int_row.getValue("Vscore_"+hab+"_"+s)))
                                        intersection_rows.updateRow(int_row)
                                    #if no vscore found, then throw error saying that this combination doesn't exist in the vscore table, break the loop. ALL activity/stressor combos will have a vscore
                                    else:
                                        if (a+", "+h) in NoVScoreList:
                                            continue
                                        else:
                                            NoVScoreList.append(a+", "+h)
                                            
                                            
                                            continue

                                    #initialize impact variable    
                                    impact = 0.0
                                    #Calculate and set impact score based on one of two cases: fishing related or non-fishing related
                                    if "cf" in act or "sportf" in act:
                                        #arcpy.AddMessage("Populating fishing gear severity scores...")
                                    #when fishing severity key is found, apply associated fishing severity to fishgear_score attribute of intersect table#when fishing severity key is found, apply associated fishing severity to fishgear_score attribute of intersect table
                                        if fishKeyValue in fishingDict:
                                            
                                            #set fishing gear score from dictionary
                                            int_row.setValue("fishgear_score_"+act, fishingDict[fishKeyValue])
                                            
                                            #collect fishing gear score, vscore and RI. calculate impact score
                                            fishgear_score = int_row.getValue("fishgear_score_"+act)                                        
                                            vscore = int_row.getValue("Vscore_"+hab+"_"+s)
                                            RI = int_row.getValue("RI_"+s)
                                            #arcpy.AddMessage(str(RI)+", "+str(fishgear_score)+", "+str(vscore))
                                            impact = fishgear_score * vscore * RI

                                            #error if fishing gear score is not found or is 0, which should not be possible for cf or sportf activities
                                            if fishgear_score is None or fishgear_score ==0:
                                                arcpy.AddError("Fishing gear score is either 0 or null. please check fishing severity table for activity code: " +str(a))                                        

                                            #set impact score to calculated value
                                            int_row.setValue("Impact_"+hab+"_"+s, impact)

                                            intersection_rows.updateRow(int_row) 
                                        #if no fishing severity found, throw message that combo has no fishing score, and skip to next line. not all activity/stressor combos will have a fishing severity (shipping, rec boating, etc.)
                                        else:

                                            if (a+", "+s) in noFishingList:
                                                continue
                                            else:
                                                noFishingList.append(a+", "+s)                            
                                    
                                    else:
                                        #collect variables for impact calculation: RI and vulnerability score. 
                                        RI = int_row.getValue("RI_"+s)
                                        vscore = int_row.getValue("Vscore_"+hab+"_"+s)

                                        #calculate impact
                                        if RI:
                                            impact = RI * vscore

                                        #set impact score to calculated value
                                        int_row.setValue("Impact_"+hab+"_"+s, impact)

                                        intersection_rows.updateRow(int_row)
                                    
                                    #arcpy.AddMessage("Calculating impact...")
                                    # ADJ_HabAREA_WT represents the activity/habitat interaction as a proportion of the entire marineArea within a grid cell. It is used to weight the vulnerability score by the habitat area
                                    adjHabArea = (int_row.getValue("Shape_Area")/int_row.getValue("MarineAREA"))
                                    
                                    #perform habitat area weighting and assigned 
                                    wtd_impact = adjHabArea*impact
                                    int_row.setValue("ADJ_HabAREA_WT", adjHabArea)
                                    int_row.setValue("Wtd_Impact", wtd_impact)
                                    intersection_rows.updateRow(int_row)

#3.1.8
            #delete the table view used to create the applicable stressor list                
            arcpy.management.Delete("vscore_table")
        if noFishingList:

            arcpy.AddWarning("the following activity and stressor combinations have no associated fishing severity score. If the activity is not fishing related then this is expected."+
                            str(noFishingList))
            # arcpy.AddWarning(noFishingList)                 
        if NoVScoreList:
            arcpy.AddWarning("the following activity and Habitat combinations have no associated Vulnerability score. Please Verify in the VScores table."+
                             str(NoVScoreList))
            # arcpy.AddWarning(NoVScoreList)  
        
        arcpy.AddMessage("Output workspace: "+outputWorkspace)

        return
############################################################# END Step 3 #####################################################

class Step4(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "4. Calculate Sum Impact Scores (per activity)"
        self.description = """This step calculates the impact scores for each activity-habitat combination, and 
        calculates the sum impact scores per activity, across all habitats. This tool  will generate a large number
        of output tables, and a separate output workspace is recommended for the outputs of this step. 
        
        It is possible to run this step one activity at a time, or in small groups of activities. For activities that are spatially
        extensive, it may be more efficient to run this step one activity at a time, and in small groups of habitats."""
        self.canRunInBackground = False

    def getParameterInfo(self):
        ##  Define parameters

        param0 = arcpy.Parameter(
            displayName="Input Workspace",
            name="inputWorkspace",
            datatype=["DEFeatureDataset","DEWorkspace"],
            parameterType="Required",
            direction="Input")
        param0.value = os.path.join(os.path.dirname(__file__),r'CI_MarineFootprint_Outputs.gdb\Impact')

        param1 = arcpy.Parameter(
            displayName="Output Workspace",
            name="outputWorkspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        param1.value = os.path.join(os.path.dirname(__file__),r'CI_MarineFootprint_OutputTables.gdb')

        param2 = arcpy.Parameter(
            displayName="Activity-Stressor Table",
            name="stressortable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        param2.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\master_stressor_table')

        param3 = arcpy.Parameter(
            displayName="Reference Grid (vector) Feature Class",
            name="grid",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")
        param3.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\baselayers\pu_1km_Marine')

        param4 = arcpy.Parameter(
            displayName="Activity Wildcards",
            name="act",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue = True)

        param5 = arcpy.Parameter(
            displayName="Only run cumulative tables",
            name="cumultablesonly",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        param5.value = False

## ---------------- Added by KChan May 11 2016 
        param6 = arcpy.Parameter(
            displayName = "Scenario (current/future/protected)",
            name = "scn",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        param6.filter.list = ["c","f","p"]
## -------------------------
        param7 = arcpy.Parameter(
            displayName = "Habitat workspace",
            name = "habitatWorkspace",
            datatype = ["DEFeatureDataset","DEWorkspace"],
            parameterType = "Required",
            direction = "Input"
        )
        param7.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\habitats')

        
        param8 = arcpy.Parameter(
            displayName="Habitat feature classes",
            name="habitatFCs",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue = True)

        params = [param0,param1,param2,param3,param4,param5,param6,param7,param8] ## param6 added - KC 
        return params
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
#4.0.1
        #create list of activities that are able to be processed through step 4
        activities = set()
        #if there is no list of activities already then execute code
        if not parameters[4].filter.list:
            #populate a set of all activities from the master stressor table
            if parameters[2].valueAsText:
                rows = arcpy.da.SearchCursor(parameters[2].valueAsText,["ACTIVITY_CODE"])
                for row in rows:
                    activities.add(row[0])
                del rows
            #if the inputs gdb has been set and activities set has been populated 
            if parameters[0].valueAsText and activities:
                #set the workspace to the input workspace, list all feature classes in the input workspace and loop through activities looking for an activity to be present in the feature classes
                arcpy.env.workspace = parameters[0].valueAsText
                features = arcpy.ListFeatureClasses()
                inputselection = set()
                for f in features:
                    for a in activities:
                        if a in f:
                            inputselection.add(a)
                parameters[4].filter.list = list(sorted(inputselection))

        if parameters[7]:
            #set workspace to habitat workspace and list feature classes in workspace
            arcpy.env.workspace = parameters[7].value
            habList = []
            fcList = arcpy.ListFeatureClasses()
            for fc in fcList:
                habList.append(os.path.basename(fc))

            parameters[8].filter.list = sorted(habList)
        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
#4.1.1
        if parameters[4].valueAsText:
            selected = parameters[4].valueAsText.split(";")
            if len(selected) > 3:
                parameters[4].setWarningMessage("You have selected more than 3 activities; the processing may take a while!")
            elif 3 > len(selected) > 0:
                parameters[4].clearMessage()
        else:

            parameters[4].setWarningMessage("You have not selected any activities; the tool will process all activities. This may take a while!")
        return

    def execute(self, parameters, messages):
        ##  The source code of the tool.

        ##  Read in parameters
        inputWorkspace = parameters[0].ValueAsText
        outputWorkspace = parameters[1].ValueAsText
        stressortable = parameters[2].ValueAsText
        grid = parameters[3].ValueAsText
        act = parameters[4].ValueAsText
        cumultablesonly = parameters[5].Value
        scn = parameters[6].ValueAsText ## scenario parameter added - KC
        habitatWorkspace = parameters[7].valueAsText
        habitatFCs = parameters[8].ValueAsText
        
        ##  Environment settings

        arcpy.env.workspace = inputWorkspace

        #create empty lists to hold all activity, habitat and code combos that have no impact table for both sum tables and cumulative tables
        sumErrorList = []
        cumulErrorList = []
        habErrorList = []

#4.2.1
        ##  Create a set for activities and gridcodes
        activities = set()
        gridcodes = set()
        habitats = []

        ##  Fill activities set
        if act:
            acts = act.split(";")
            for a in acts:
                activities.add(a)

        ##  Fill gridcodes set
        pu_rows = arcpy.da.SearchCursor(grid,["UNIT_ID"])
        for pu in pu_rows:
            gridcodes.add(pu[0])
        del pu_rows

        # populate list of habitats
        habitats = habitatFCs.split(";")
        for hab in habitats:
            hf = os.path.join(habitatWorkspace,hab)
            arcpy.AddMessage("Processing Habitat layer: " + str(hab))
            

            # pull list of unique HabitatCODEs from attributes of habitat feature classes 
            with arcpy.da.SearchCursor(hf, ["HabitatCODE"]) as cursor:
                HabitatCODE = sorted({row[0] for row in cursor})

            if not HabitatCODE:
                arcpy.AddError("Unable to match files with a habitat. The filenames of the Habitat feature classes may be incorrect.\n"+
                                         "Feature class names are case sensitive 2-letter codes:\n"+
                                         "\"benthic habitats = bh\"\n"+
                                         "\"deep pelagic habitats = dp\"\n"+
                                         "\"eelgrass habitats = eg\"\n"+
                                         "\"kelp habitats = kp\"\n"+
                                         "\"shallow pelagic habitats = sp\"\n"+
                                         "\"sponge reef habitats = sr")
                return

            arcpy.AddMessage("Associated Habitat Codes: "+str(HabitatCODE))
        
#4.2.2
            #check to see if option for cumulative tables only selected.
            if not cumultablesonly:
                arcpy.AddMessage(activities) #for debugging
                for a in activities:
                   
                    #set the workspace
                    arcpy.env.workspace = inputWorkspace
                    #create a list of all feature classes that contain the current activity and habitat
                    featurelist = arcpy.ListFeatureClasses(scn+"_"+a+"_*"+hab+"_*")

                    if not featurelist:
                        arcpy.AddWarning("Not found: features in the Input Workspace for the "+str(a)+" and "+str(hab)+" combination. \n"+
                                                 "Double-check the file path and ensure that the appropriate feature classes from Step 4 are present.\n"+
                                                 "If you continue seeing this error message, try restarting ArcGIS.\n")
                        continue
        #4.2.3
                    #create impact tables using statistics  calculation of impact tables
                    arcpy.AddMessage("\nImpact Tables\n")
                    ##  Sum Area-Weighted Impact by grid cell
                    for f in featurelist:
                        arcpy.AddMessage("Processing Feature: "+str(f))
                        if a in f:
                            try:
                                arcpy.analysis.Statistics(f, os.path.join(outputWorkspace,f+"_impact"), [["Wtd_Impact", "SUM"]], "UNIT_ID")
                            except:
                                arcpy.AddError("Table statistics for "+f+" failed. Please check for data corruption and restart ArcGIS Pro.")
                                return
                  
            
            ##  Sum Impacts across stressors per activity
            if not cumultablesonly:
                arcpy.AddMessage("\nSum Impact Tables\n")
#4.2.4
            
                for a in activities:
#4.2.4.0
                    arcpy.AddMessage("Processing "+a)

                    arcpy.env.workspace = outputWorkspace 
                    
                    #populate a list of stressors that are relevant to the current activity
                    stressors = []
                    stressor_rows = arcpy.da.SearchCursor(stressortable,["ACTIVITY_CODE","STRESSOR_CODE","Sub_Activity"])
                    #row[0] = ACTIVITY_CODE
                    #row[1] = STRESSOR_CODE
                    #row[2] = Sub_Activity
                    for row in stressor_rows:
                        if row[0] == a:
                            stressors.append(row[1].strip())
                    stressor_rows.reset()
                
                    #loop through each habitat code and create a new table of sum impact    
                    for code in HabitatCODE:
                        nonefound = True
                        featurelist = arcpy.ListTables(scn+"_"+a+"*"+hab+"*"+code+"_impact") ## scenario added - KC  
                        if featurelist:
                            nonefound = False
    #4.2.4.2
                            #Create a new table to store sum impact scores
                            table = arcpy.management.CreateTable(outputWorkspace, scn+"_"+a+"_sum_impact_"+hab+"_"+code) ## scenario added - KC
                            
                            arcpy.AddMessage("Processing "+str(table))
                            arcpy.management.AddField(table,"UNIT_ID","LONG")
                            arcpy.management.AddField(table,"Sum_Impact_"+a,"FLOAT")
                            
                            
                            #insert cursor to add all unitIDs to the new table
                            insert = arcpy.da.InsertCursor(table,["UNIT_ID"])
                            for g in gridcodes:
                                insert.insertRow([g])
                            del insert
    #4.2.4.3
                            #for each stressor associated with the activity, add a new column to the table and copy the impact score from the statistic table above
                            for s in stressors:
                                feature = None
                                #set the feature variable used in cursors if the stressor is contained in the file name/path
                                for f in featurelist:
                                    if s in f:
                                        feature = f
                                if feature:
                                   #build data dictionary for feature to link unitID with wtd_Impact. restrict fields to unitID and Wtd_Impact
                                    #unit[0] = UNIT_ID
                                    #unit[1] = SUM_Wtd_Impact
                                    unitDict = {}
                                    unitCursor = arcpy.da.SearchCursor(feature, ["UNIT_ID", "SUM_Wtd_Impact"])
                                    for unit in unitCursor:
                                        unitDict.update({unit[0]:unit[1]})
                                    del unitCursor
                              
                                    #add a field for impact from the stressor
                                    arcpy.management.AddField(table,"Impact_"+s,"DOUBLE")
                                    #update cursor to apply Wtd_Impact to Sum_Impact_activity field use data analysis update cursor to improve processing speed as cursor is used iteratively
                                    #unitID[0] = UNIT_ID
                                    #unitID[1] = Sum_Impact_activity : where activity represents the activity code
                                    updCursor = arcpy.da.UpdateCursor(table, ["UNIT_ID", "Impact_"+s])
                                    for unitID in updCursor:
                                        unitIDKey = unitID[0]
                                        if unitIDKey in unitDict:
                                            #set Sum_Impact_activity to the Wtd_Impact value from the dictionary of matching UNIT_ID
                                            unitID[1]= unitDict[unitIDKey]
                                            updCursor.updateRow(unitID)
                                    del updCursor, unitDict

                            #update cursor to calculate and apply cumulative impact
                            sumfields = arcpy.UpdateCursor(table)
                            for row in sumfields:
                                #running total of each stressor's impact for an activity and habitat
                                total = 0.0
                                indicator = False
                                for s in stressors:
                                    try:
                                        if row.getValue("Impact_"+s) is not None:
                                            #increment the total by the value of the current row
                                            total += float(row.getValue("Impact_"+s))
                                            indicator = True
                                    except:
                                        continue
                                if indicator == True:
                                    row.setValue("Sum_Impact_"+a,total)
                                    sumfields.updateRow(row)
                                if row.getValue("Sum_Impact_"+a) is None:
                                    sumfields.deleteRow(row)
                            del sumfields
                            
                        if nonefound:
                            #if no data for this activity, habitat, and habitat code combo exist, add the combo to a list to be printed at the end of the tool
                            sumErrorList.append(a+", "+hab+", "+code)
                
                #after activity loop is closed and stressor cursor is no longer needed delete cursor
                del stressor_rows        

        arcpy.AddMessage("Habitats already processed for sum impacts: "+str(habitats))
        
#4.2.5
        ##  Cumulative Impacts across habitat codes per activity
        arcpy.AddMessage("\nCumulative Tables\n")

        for a in activities:
            arcpy.AddMessage("Processing sum impacts across habitat codes for "+a)
            arcpy.env.workspace = outputWorkspace

            for h in habitats:
                
                nonefound = True
                #create a list of sum impact tables created in above codeblocks
                #change featurelist to tableList
                featurelist = arcpy.ListTables(scn+"_"+a+"_sum_impact*"+h+"*") ## scenario added - KC
                if featurelist:
                    nonefound = False
                    #create a new table for the cumulative impact of the activity in that habitat
                    table = arcpy.management.CreateTable(outputWorkspace, scn+"_"+a+"_cumul_impact_"+h) ## scenario added - KC
                    arcpy.management.AddField(table,"UNIT_ID","LONG")
                    arcpy.management.AddField(table,"Cumul_Impact_"+a,"FLOAT")
                    #insert cursor to add all possible grid codes to the new table
                    insert = arcpy.da.InsertCursor(table,["UNIT_ID"])
                    for g in gridcodes:
                        insert.insertRow([g])
                    del insert
                else: 
                    continue #go to next habitat

                hf = os.path.join(os.path.dirname(__file__),r"CI_InputData.gdb\habitats", h)

                with arcpy.da.SearchCursor(hf, ["HabitatCODE"]) as cursor:
                    HabitatCODE = sorted({row[0] for row in cursor})
                
                if featurelist:
                    for code in HabitatCODE:
                        code = str(code)
                        # feature = None
                        for feature in featurelist:
                            if code in feature:
                                arcpy.management.AddField(table,"Impact_"+code,"DOUBLE")
                                
                                #build data dictionary for feature to link unitID with Sum_Impact. restrict fields to unitID and Sum_Impact
                                #unit[0] = UNIT_ID
                                #unit[1] = Sum_Impact
                                cumulDict = {}
                                cumulCursor = arcpy.da.SearchCursor(feature, ["UNIT_ID", "Sum_Impact_"+a])
                                for cumulRow in cumulCursor:
                                    cumulDict.update({cumulRow[0]:cumulRow[1]})
                                del cumulCursor
                                if feature:
                                    #update cursor to apply Wtd_Impact to Sum_Impact_activity field use data analysis update cursor to improve processing speed as cursor is used iteratively
                                    #row[0] = UNIT_ID
                                    #row[1] = Cumul_Impact_activity : where activity represents the activity code
                                    updCursor = arcpy.da.UpdateCursor(table, ["UNIT_ID", "Impact_"+code])
                                    for row in updCursor:
                                        cumulKey = row[0]
                                        if cumulKey in cumulDict:
                                            #set Cumul_Impact_activity to the Sum_Impact_a value from the dictionary of matching UNIT_ID
                                            row[1]= cumulDict[cumulKey]
                                            updCursor.updateRow(row)

                                    del updCursor, cumulDict
                       
                #update cursor to calculate cumulative impact and apply it to new table.               
                sumfields = arcpy.UpdateCursor(table)
                for row in sumfields:
                    total = 0.0
                    indicator = False
                    for code in HabitatCODE:
                        code = str(code)
                        try:
                            if row.getValue("Impact_"+code) is not None:
                                indicator = True
                                total += float(row.getValue("Impact_"+code))
                        except:
                            continue
                    if indicator == True:
                        row.setValue("Cumul_Impact_"+a,total)
                        sumfields.updateRow(row)
                    if row.getValue("Cumul_Impact_"+a)is None:              
                        sumfields.deleteRow(row)
                del sumfields

                if nonefound:
                    #if there is no activity in this habitat, add the activity and habitat combo to a list to be added at the end as a warning
                    cumulErrorList.append(a+", "+h)


        
        

        ##  Cumulative impacts across all habitats per activity 
        arcpy.AddMessage("\nProcessing cumulative impacts across all habitats per activity.\n")
        
        for a in activities:
            arcpy.env.workspace = outputWorkspace
            
            #create list of cumulative impact tables created in code block above
            featurelist = arcpy.ListTables(scn+"_"+a+"_cumul_impact_*") ## scenario added - KC

            if featurelist:
                arcpy.AddMessage("Processing "+a)
                nonefound = False
                table = arcpy.management.CreateTable(outputWorkspace, scn+"_"+a+"_cumul_impact") ## scenario added - KC
                arcpy.management.AddField(table,"UNIT_ID","LONG")
                arcpy.management.AddField(table,"Cumul_Impact_"+a,"FLOAT")

                insert = arcpy.da.InsertCursor(table,["UNIT_ID"])
                for g in gridcodes:
                    insert.insertRow([g])
                del insert

                
                for feature in featurelist:
                    h = feature[-2:] #pull habitat from table name
                    arcpy.management.AddField(table,"Cumul_Impact_"+h,"FLOAT")
                    #build data dictionary for feature to link unitID with wtd_Impact. restrict fields to unitID and Wtd_Impact
                    #cumulHabRow[0] = UNIT_ID
                    #cumulHabRow[1] = cumul_Impact_a
                    habDict = {}
                    cumulHabCursor = arcpy.da.SearchCursor(feature, ["UNIT_ID", "Cumul_Impact_"+a])
                    for cumulHabRow in cumulHabCursor:
                        habDict.update({cumulHabRow[0]:cumulHabRow[1]})
                    del cumulHabCursor
                    if feature:
                        #update cursor to apply Wtd_Impact to Sum_Impact_activity field use data analysis update cursor to improve processing speed as cursor is used iteratively
                        #cumulHabID[0] = UNIT_ID
                        #cumulHabID[1] = Sum_Impact_activity : where activity represents the activity code
                        updHabCursor = arcpy.da.UpdateCursor(table, ["UNIT_ID", "Cumul_Impact_"+h])
                        for cumulHabID in updHabCursor:
                            cumulHabKey = cumulHabID[0]
                            if cumulHabKey in habDict:
                                #set Sum_Impact_activity to the Wtd_Impact value from the dictionary of matching UNIT_ID
                                cumulHabID[1]= habDict[cumulHabKey]
                                updHabCursor.updateRow(cumulHabID)
                            else:

                                continue
                        del updHabCursor, habDict

            arcpy.env.workspace = outputWorkspace
            cumultables = arcpy.ListTables(scn+"_"+a+"_cumul_impact")
            for table in cumultables:
                sumfields = arcpy.UpdateCursor(table)
                #for h in habitats:
                for row in sumfields:
                    total = 0.0
                    indicator = False
                    
                    for h in habitats:
                        try:
                            if row.getValue("Cumul_Impact_"+h) is not None:
                                indicator = True
                                total += float(row.getValue("Cumul_Impact_"+h))
                        except:
                            pass
                            #arcpy.AddWarning("No intersection of " + a + " and habitat " + h + " found. Proceeding to next habitat")
                        
                        if indicator == True:
                            row.setValue("Cumul_Impact_"+a,total)
                            sumfields.updateRow(row)
                            # if the calculated cumulative impact for all activities is null, then that row should be deleted.
                            if row.getValue("cumul_Impact_"+a) is None:
                                sumfields.deleteRow(row)

                del sumfields

            if nonefound:
                habErrorList.append(a+", "+h)
        
        #if there are "error lists" that have entries, dump the list of combinations as warnings.
        if sumErrorList:
            arcpy.AddWarning("Impact tables for the following activity, habitat, and habitat code combinations were not found. sum_impact tables were not generated.\n"+
                                                    "If you don't think you should be seeing this message, please check the data or restart ArcGIS Pro and try again.\n")
            arcpy.AddWarning(sumErrorList)
        if cumulErrorList:
            arcpy.AddWarning("Sum_Impact tables for the following activity and habitat were not found. cumul_impact tables were not generated.\n"+
                                        "If don't think you should be seeing this message, please check the data or restart ArcGIS Pro and try again.")
            arcpy.AddWarning(cumulErrorList)
        if habErrorList:    
            arcpy.AddWarning("Cumulative impact tables for the following tables were not found. Cumulative Habitat impact tables were not generated. If you don't think you should be getting this message, please check the data or restart ArcGIS Pro and try again.")
            arcpy.AddWarning(habErrorList)
                    
        arcpy.ResetEnvironments()
        return
        
###################################################################################################################    
class Step5(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "5. Calculate Cumulative Impact Scores (per habitat and across habitats)"
        self.description = """This step calculates the cumulative impact scores for each habitat across all activities, 
        and across all activities and habitats. In order to calculate a cumulative impact score across all activities
        and habitats, the tool must be run for all activity codes and habitats in the analysis.
        
        Cumulative Impacts for Sectors: To calculate the cumulative impact score for a subset of activities, (e.g., a sector),
        the user must input a sector descriptor to name the output geodatabase and a sector code to be used as a prefix for the
        output tables.
         
        Cumulative Impacts for all activities: When generating the final cumulative impacts calculation taking into account all
        activities and all habitats, please use uppercase "ALL" for the sector descriptor and lowercase "all" for the sector code.
        """
        self.canRunInBackground = False

    def getParameterInfo(self):
        ##  Define parameters

        param0 = arcpy.Parameter(
            displayName="Input Workspace",
            name="inputWorkspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        param0.value = os.path.join(os.path.dirname(__file__),r'CI_MarineFootprint_OutputTables.gdb')
        

        param1 = arcpy.Parameter(
            displayName="Master Stressor Table",
            name="stressortable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        param1.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\master_stressor_table')
        

        param2 = arcpy.Parameter(
            displayName="Reference vector grid",
            name="grid",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")
        param2.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\baselayers\pu_1km_Marine')

        param3 = arcpy.Parameter(
            displayName="Activity Wildcards",
            name="activity",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue = True)
        
        param4 = arcpy.Parameter(
            displayName = "Scenario",
            name = "scenario",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        param4.filter.list = ["c","f","p"]

        param5 = arcpy.Parameter(
            displayName="Sector Descriptor (for geodatabase name) ",
            name="sectorDesc",
            datatype = "GPString",
            parameterType="Required",
            direction="Input")

        param6 = arcpy.Parameter(
            displayName="Habitat Workspace",
            name="habitatWorkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")
        param6.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\habitats')

        param7 = arcpy.Parameter(
            displayName="Habitat feature classes",
            name="habitatFCs",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue = True)
        param7.enabled = False
                
        
        param8 = arcpy.Parameter(
            displayName="Sector code (for prefix)",
            name = "sector",
            datatype="GPString",
            parameterType="Required",
            direction = "Input"
        )


        param9 = arcpy.Parameter(
            displayName = "Select which part(s) of the analysis to run:",
            name = "runParts",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        param9.filter.list = ["Part 1 only: Calculate sum impact per habitat",
                               "Part 2 only: Calculate cumulative impacts across all habitats",
                               "Run Part 1 and 2: Run all calculations"]

        param10 = arcpy.Parameter(
            displayName="Overwrite existing output geodatabase for this sector",
            name = "delGDB",
            datatype="GPBoolean",
            parameterType = "Optional",
            direction="Input"
        )
        param10.value = False

        params = [param0,param1,param2,param3,param4,param5,param6,param7,param8,param9,param10] 
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        #fill a a list of activities 
        activities = set()
        if not parameters[3].filter.list:
            if parameters[1].valueAsText:
                rows = arcpy.da.SearchCursor(parameters[1].valueAsText,["ACTIVITY_CODE"])
                for row in rows:
                    activities.add(row[0])
            if parameters[0].valueAsText and activities:
                arcpy.env.workspace = parameters[0].valueAsText
                features = arcpy.ListTables()
                inputselection = set()
                for f in features:
                    for a in activities:
                        if a in f:
                            inputselection.add(a)
                parameters[3].filter.list = list(sorted(inputselection))

        if parameters[9].valueAsText == "Part 1 only: Calculate sum impact per habitat":
            parameters[7].enabled = True
        else:
            parameters[7].enabled = False
        
        
        if parameters[6]:
            #set workspace to habitat workspace and list feature classes in workspace
            arcpy.env.workspace = parameters[6].value
            habList = []
            fcList = arcpy.ListFeatureClasses()
            for fc in fcList:
                habList.append(os.path.basename(fc))

            parameters[7].filter.list = sorted(habList)
            
        if parameters[9].valueAsText == "Part 2 only: Calculate cumulative impacts across all habitats":
            parameters[10].value = False
            parameters[10].enabled = False
                
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        parameters[5].setWarningMessage("Please note: This input will be used to name the output geodatabase.")
        
        if parameters[8].valueAsText == "Run Part 1 and 2: Run all calculations":
            parameters[8].setWarningMessage("Please note: if a large amount of datasets need to be processed, running all the calculations in one go may take a very long time. Please consider running the analysis in 2 parts.")
        elif parameters[8].valueAsText == "Part 2 only: Calculate cumulative impacts across all habitats":
            parameters[8].setWarningMessage("Please ensure that all expected results tables from Part 1 are present in the geodatabase before running Part 2.")
            
        
        return

    def execute(self, parameters, messages):
        ##  The source code of the tool.

        ##  Read in parameters
        inputWorkspace = parameters[0].ValueAsText
        stressortable = parameters[1].ValueAsText
        grid = parameters[2].ValueAsText
        activity = parameters[3].ValueAsText
        scn = parameters[4].ValueAsText 
        sectorDesc = parameters[5].ValueAsText
        habitatWorkspace =  parameters[6].ValueAsText
        habitatFCs = parameters[7].ValueAsText
        sector = parameters[8].ValueAsText
        runParts = parameters[9].ValueAsText
        delGDB = parameters[10].value
        
    
        if runParts == "Part 1 only: Calculate sum impact per habitat":
            noCumul = True
            cumultablesonly = False
        elif runParts == "Part 2 only: Calculate cumulative impacts across all habitats":
            noCumul = False
            cumultablesonly = True
        elif runParts == "Run Part 1 and 2: Run all calculations":
            noCumul = False
            cumultablesonly = False        

        #search the directory for geodatabases with the sector descriptor in them
        arcpy.env.workspace = os.path.dirname(__file__)
        gdbList = arcpy.ListWorkspaces("CIM_Table_*")
        outputGDBName = "CIM_Tables_"+str(sectorDesc)
        outputPath = os.path.dirname(__file__)

        if delGDB == True:
        #only run script if at user wants to delete previous GDB and create new
            for gdb in gdbList:
                if "CE" in gdb:
                    continue
                elif str(os.path.basename(gdb))== "CIM_Tables_"+str(sectorDesc)+".gdb":
                    arcpy.management.Delete(gdb)
                    arcpy.AddMessage("Deleted pre-existing "+sectorDesc+" database")

        outputGDBName = "CIM_Tables_"+str(sectorDesc)+".gdb"
        outputGDBPath = os.path.join(outputPath, outputGDBName)
        
        
        #if gdb not in directory, create new gdb with appropriate name            
        if arcpy.Exists(outputGDBPath):
            arcpy.AddMessage("Output Geodatabase exists in directory")
            outputWorkspace = outputGDBPath
            arcpy.env.workspace = outputWorkspace
        else:
            arcpy.AddMessage("Output Geodatabase does not exist in directory, one will be created")
            #after checking for and deleting existing geodatabases for the sector descriptor, create a new geodatabase for the results to be stored in.
            #set the spatial reference for the new file gdb
            sr = arcpy.Describe(grid).spatialReference
            
            arcpy.env.outputCoordinateSystem = sr

            outputGDB = arcpy.management.CreateFileGDB(outputPath, outputGDBName, "CURRENT")
            #In order to set the environment workspace to a newly created GDB, you must use the getOutput method to pull the result
            outputWorkspace = outputGDB.getOutput(0)
            arcpy.AddMessage("Created new file geodatabase for " + sectorDesc + " cumulative impact outputs")
            ##  set workspace to newly created workspace
            arcpy.env.workspace = outputWorkspace
        

        
        arcpy.AddMessage("Output workspace: "+str(outputWorkspace))
        
        ##  Create a set for activities and gridcodes
        activities = set()
        gridcodes = set()

        ##  Create new cursor to iterate through table
        stressor_rows = arcpy.da.SearchCursor(stressortable,["ACTIVITY_CODE","STRESSOR_CODE"])
        pu_rows = arcpy.da.SearchCursor(grid,["UNIT_ID"])

        ##  Fill activities set
        if activity:
            acts = activity.split(";")
            for a in acts:
                activities.add(a)
        elif not activity:
            for row in stressor_rows:
                activities.add(row[0])
            stressor_rows.reset()

        ##  Fill gridcodes set
        for pu in pu_rows:
            gridcodes.add(pu[0])
        
        # ## Get list of habitats
        if runParts == "Part 1 only: Calculate sum impact per habitat":
            #create list of habitat fcs from habitat string parameter
            habitats = habitatFCs.split(";")
        else:
            #create list of habitats as all habitats in habitat workspace
            arcpy.env.workspace = habitatWorkspace
            habitats = arcpy.ListFeatureClasses()

        ##  Sum Impacts across all activities, for each HabitatCODE
        arcpy.env.workspace = inputWorkspace
        
        if cumultablesonly == "true":
            arcpy.AddMessage("Skip cumulative impact calculations for each habitat code.")
        else:
            arcpy.AddMessage("Processing cumulative impacts for each habitat code.")
            
            for h in habitats:
                arcpy.AddMessage("Processing "+h)
                hf = os.path.join(habitatWorkspace,h)
                with arcpy.da.SearchCursor(hf, ["HabitatCODE"]) as cursor:
                    HabitatCODE = sorted({row[0] for row in cursor})
                        

                    if not HabitatCODE:
                        arcpy.AddError("Unable to match files with a habitat. The filenames of the Habitat feature classes may be incorrect.\n"+
                                         "Feature class names are case sensitive 2-letter codes:\n"+
                                         "\"benthic habitats = bh\"\n"+
                                         "\"deep pelagic habitats = dp\"\n"+
                                         "\"eelgrass habitats = eg\"\n"+
                                         "\"kelp habitats = kp\"\n"+
                                         "\"shallow pelagic habitats = sp\"\n"+
                                         "\"sponge reef habitats = sr")
                        return

                    arcpy.AddMessage("Habitat codes: "+str(HabitatCODE))

                #set workspace to input workspace specified by user
                arcpy.env.workspace = inputWorkspace

                for code in HabitatCODE:
                    nonefound = True
                    featurelist = arcpy.ListTables(scn+"*_sum_impact_"+h+"_"+code) ## scenario added - KC
                    arcpy.AddMessage("List of features: "+str(featurelist))
                    if featurelist:
                        arcpy.AddMessage("Processing "+h+" "+str(code))
                        nonefound = False
                      
                        table = arcpy.management.CreateTable(outputWorkspace, scn+"_"+sector+"_cumul_impact_"+h+"_"+str(code)) ## scenario added - KC
                        arcpy.management.AddField(table,"UNIT_ID","LONG")
                        arcpy.management.AddField(table,"Cumul_Impact_"+code,"FLOAT")
                        insert = arcpy.da.InsertCursor(table,["UNIT_ID"])
                        
                        for g in gridcodes:
                            insert.insertRow([g])
                        del insert
                        
                        actCodeSubset = []

                        for a in activities:
                            for f in featurelist:
                                
                                
                                #match name of activity sum impact table to the exact activity sum impact table being considered
                                if f == scn+"_"+a+"_sum_impact_"+h+"_"+code:
                                    #arcpy.AddMessage("Processing " + os.path.basename(f)) #debug
                                    #build dictionary of sum_impacts accross habitat/code features
                                    featDict = {}
                                    featSearch = arcpy.da.SearchCursor(f, ["UNIT_ID", "Sum_Impact_"+a])
                                    for feat in featSearch:
                                        #feat[0] = UNIT_ID
                                        #feat[1] = Sum_Impact_ACTIVITY
                                        featDict.update({feat[0]:feat[1]})

                                    #inform user that the activity being considered is relevant     
                                    #arcpy.AddMessage("    Found "+a)
                                    
                                    #add valid dataset into a subset, so that only activity codes with valid intersections are considered
                                    actCodeSubset.append(str(a))
                                    #arcpy.AddMessage(actCodeSubset) #debug
                                    
                                    #add field for sum_impact_activity in the cumulative habitat_code table. 
                                    arcpy.management.AddField(table,"Sum_Impact_"+a,"DOUBLE")

                                    #update cursor to apply sum_impact_activity to cumul_impact_habitat_habitatcode
                                    habUpdate = arcpy.da.UpdateCursor(table, ["UNIT_ID", "Sum_Impact_"+a])
                                    for habRow in habUpdate:
                                        habKey = habRow[0]
                                        if habKey in featDict:
                                            habRow[1] = featDict[habKey]
                                            habUpdate.updateRow(habRow)
                                    del habUpdate, featSearch


                        arcpy.AddMessage("Activity Subset for " + code + ": " + str(actCodeSubset))
                        
                        noSumImpactList = set()

                        #calculate cumulative impact for current habitat code
                        sumfields = arcpy.UpdateCursor(table)
                        for row in sumfields:
                            total = 0.0
                            indicator = False
                            # for a in activities:
                            for a in actCodeSubset:
                                try:
                                    if row.getValue("Sum_Impact_"+a) is not None:
                                        total += float(row.getValue("Sum_Impact_"+a))
                                        indicator = True
                                except:
                                    noSumImpactList.add(a+", " + code)
                                    continue
                            if indicator == True:
                                row.setValue("Cumul_Impact_"+str(code),total)
                                sumfields.updateRow(row)                                
                        del sumfields

                        #if there is one or more datasets with no activity/habitat combo, display the combinations with no intersection.
                        if len(noSumImpactList) > 1:
                            arcpy.AddWarning("sum_impact table not found for the following activity/habitat combinations. Please check if this is expected vs results of step 4")
                            arcpy.AddWarning(noSumImpactList)

                        #after cumulative impact is calculated, if cumulative impact value is null (no impact in that habitat code), delete the row for faster processing in later process
                        deleteNulls = arcpy.da.UpdateCursor(table, "Cumul_Impact_"+code)
                        for nullRow in deleteNulls:
                            if nullRow[0] is None:
                                deleteNulls.deleteRow()
                        del deleteNulls
                    if nonefound:
                        arcpy.AddWarning("WARNING: sum_impact tables for "+h+" "+code+" habitat codes NOT FOUND.\n"+
                                                        "If you continue to see this error message after checking the workspace and activity code, please restart ArcMap/Catalog and try again.\n")                    

       
                  
        ##  Sum Impacts for all activities across all HabitatCODES, per habitat set (bh, dp, eg, kp, etc)

        arcpy.env.workspace = outputWorkspace
        if cumultablesonly == "true":
            arcpy.AddMessage("Skip cumulative impact calculation for each habitat set.")
        else:
            arcpy.AddMessage("Processing cumulative impacts for "+str(habitats))
            
            for h in habitats:
                hf = os.path.join(habitatWorkspace,h)
                with arcpy.da.SearchCursor(hf, ["HabitatCODE"]) as cursor:
                    HabitatCODE = sorted({row[0] for row in cursor})
                        
                    if not HabitatCODE:
                        arcpy.AddError("Unable to match files with a habitat. The filenames of the Habitat feature classes may be incorrect.\n"+
                                        "Feature class names are case sensitive 2-letter codes:\n"+
                                        "\"benthic habitats = bh\"\n"+
                                        "\"deep pelagic habitats = dp\"\n"+
                                        "\"eelgrass habitats = eg\"\n"+
                                        "\"kelp habitats = kp\"\n"+
                                        "\"shallow pelagic habitats = sp\"\n"+
                                        "\"sponge reef habitats = sr")
                        return

                    arcpy.AddMessage("Habitat codes: "+str(HabitatCODE))
            
                nonefound = True
                feature = None

                arcpy.env.workspace = outputWorkspace
                table2 = arcpy.management.CreateTable(outputWorkspace, scn+"_"+sector+"_"+"cumul_impact_"+h) ## scenario added - KC
                arcpy.AddMessage("      Generated output table: "+ str(table2))

                arcpy.management.AddField(table2,"UNIT_ID","LONG")
                arcpy.management.AddField(table2,"Cumul_Impact_"+h,"FLOAT")

                #insert cursor to add all grid codes to new table
                insert = arcpy.da.InsertCursor(table2,["UNIT_ID"])
                for g in gridcodes:
                    insert.insertRow([g])
                del insert

                for code in HabitatCODE:

                    featurelist = arcpy.ListTables(scn+"_"+sector+"_cumul_impact_"+h+"_"+code) ## scenario added - KC
                    if featurelist:
                        nonefound = False
                        for f in featurelist:
                            if f == scn+"_"+sector+"_cumul_impact_"+h+"_"+code:

                                #build dictionary to store UNIT_ID and cumulative impact pairs
                                habDict = {}
                                
                                habSearch = arcpy.da.SearchCursor(f,["UNIT_ID", "Cumul_Impact_"+code])
                                for row2 in habSearch:
                                    habDict.update({row2[0]:row2[1]})

                                arcpy.AddMessage("Processing "+h+": "+ f)

                                arcpy.management.AddField(table2,"Cumul_Impact_"+str(code),"DOUBLE")
                                
                                #Update cursor to apply cumulative impacts  
                                updCursor2 = arcpy.da.UpdateCursor(table2, ["UNIT_ID","Cumul_Impact_"+str(code)])
                                for updRow2 in updCursor2:
                                    habKey2 = updRow2[0]
                                    if habKey2 in habDict:
                                        updRow2[1]=habDict[habKey2]
                                        updCursor2.updateRow(updRow2)
                                del updCursor2, habDict
                        
                            sumfields = arcpy.UpdateCursor(table2)
                            for row in sumfields:
                                total = 0.0
                                indicator = False
                                for code in HabitatCODE:
                                    code = str(code)
                                    try:
                                        if row.getValue("Cumul_Impact_"+code) is not None:
                                            total += float(row.getValue("Cumul_Impact_"+code))
                                            indicator = True 
                                    except:
                                        continue
                                if indicator == True:
                                    row.setValue("Cumul_Impact_"+h,total)
                                    sumfields.updateRow(row)
                            del sumfields

                #after cumulative impact is calculated, if cumulative impact value is null (no impact in that habitat), delete the row for faster processing in later process            
                deleteNulls2 = arcpy.da.UpdateCursor(table2, "Cumul_Impact_"+h)
                for nullRow2 in deleteNulls2:
                    if nullRow2[0] is None:
                        deleteNulls2.deleteRow()
                del deleteNulls2

                arcpy.env.workspace = outputWorkspace    
                if nonefound:
                    arcpy.AddWarning("WARNING: cumul_impact tables for "+h+" habitat codes NOT FOUND. \n"+
                                                "If you continue to see this error message after checking the workspace and activity code, please restart ArcMap/Catalog and try again. \n")

                
        if noCumul == False: 
            #### Start cumululative impact calculations across ALL ACTIVITIES AND ALL Habitats
            arcpy.AddMessage("\nProcessing cumulative impacts across all activities and all habitats\n")

            arcpy.env.workspace = outputWorkspace
            all_habitats_table = arcpy.management.CreateTable(outputWorkspace,  scn+"_"+sector+"_"+"cumul_impact__ALL_HABITATS") ## scenario added - KC

            arcpy.management.AddField(all_habitats_table,"UNIT_ID","LONG")
            arcpy.management.AddField(all_habitats_table,"Cumul_Impact_ALL","DOUBLE")
            
            #insert cursor to fill new table with all PU grid codes
            insert = arcpy.da.InsertCursor(all_habitats_table,["UNIT_ID"])
            for g in gridcodes:
                insert.insertRow([g])
            del insert

            arcpy.management.AddIndex(all_habitats_table, ["UNIT_ID"], "UNIT_ID_index", "UNIQUE", "ASCENDING")
            
            for h in habitats:
                nonefound = True

                featurelist = arcpy.ListTables( scn+"_"+sector+"_cumul_impact_"+h) ## scenario added - KC
                if featurelist:
                    arcpy.AddMessage("Processing "+h)
                    nonefound = False
                    arcpy.management.AddField(all_habitats_table,"Cumul_Impact_"+h,"DOUBLE")
                
                    feature = None
                    for f in featurelist:
                        if str(h) in f:
                            feature = f
                            arcpy.AddMessage("    Feature = "+str(f))

                            if feature:
                                #build dictionary for storing UNIT_ID and Cumul_Impact_h pairings for each habitat
                                valueDict = {}
                                habSearch2 = arcpy.da.SearchCursor(feature,["UNIT_ID", "Cumul_Impact_"+h])
                                for habRow2 in habSearch2:
                                    #habRow2[0] = UNIT_ID
                                    #habRow2[1] = Cumul_Impact_habitat
                                    valueDict.update({habRow2[0]:habRow2[1]})
                                arcpy.AddMessage("    Found "+str(h))

                                #update cursor to apply cumulative impact from input tables to output table
                                habUpdate2 = arcpy.da.UpdateCursor(all_habitats_table,["UNIT_ID","cumul_impact_"+h])
                                for updRow in habUpdate2:
                                    cumulKey = updRow[0]
                                    if cumulKey in valueDict:
                                        updRow[1]=valueDict[cumulKey]
                                        habUpdate2.updateRow(updRow)
                                
                    sumfields = arcpy.UpdateCursor(all_habitats_table)
                    for row in sumfields:
                        total = 0.0
                        indicator = False
                        for h in habitats:
                            try:
                                if row.getValue("Cumul_Impact_"+h) is not None:
                                    total += float(row.getValue("Cumul_Impact_"+h))
                                    indicator = True
                            except:
                                continue
                        if indicator == True:
                            row.setValue("Cumul_Impact_ALL",total)
                            sumfields.updateRow(row)
                    del sumfields

                arcpy.env.workspace = outputWorkspace
                
                if nonefound:
                    arcpy.AddWarning("WARNING: cumul_impact tables for "+h+" NOT FOUND.\n"+
                                                "If you continue to see this error message after checking the workspace and activity code, please restart ArcMap/Catalog and try again.\n") 
        return
                


######################################################################################################################

###################################################################################################################    
class Step6(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "6. Spatialize Data Tables"
        self.description = """This step will join geodatabase tables to the reference vector grid for spatialization
        and mapping. The input tables will require a UNIT_ID to be used as a join field. Each table entered will be result 
        in an output feature class that will be saved in the same workspace the table is in."""
        self.canRunInBackground = False

    def getParameterInfo(self):
        ##  Define parameters

        param0 = arcpy.Parameter(
            displayName="Reference vector grid",
            name="grid",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")
        param0.value = os.path.join(os.path.dirname(__file__),r'CI_InputData.gdb\baselayers\pu_1km_Marine')

        param1 = arcpy.Parameter(
            displayName="Tables to spatialize",
            name="tables",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            multiValue = True)
        
        params = [param0, param1]
        return params
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
#5.0.1


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
        return

    def execute(self, parameters, messages):
        ##  The source code of the tool.

        #read in parameters
        #outputWorkspace = parameters[0].ValueAsText
        grid = parameters[0].ValueAsText
        tables = parameters[1].ValueAsText

        tableList = tables.split(";")
        arcpy.AddMessage(tableList)

        #iterate through tables in table list
        for table in tableList:
            arcpy.AddMessage("Processing "+ str(table)+"...")
            outputWorkspace = os.path.dirname(table)
            outputFCName = os.path.basename(table)+"__FC"
            outputFCPath = os.path.join(outputWorkspace,outputFCName)
            arcpy.env.workspace = outputWorkspace

            #make a copy of the grid to do the join for each CI table
            outputFC = arcpy.management.CopyFeatures(grid,outputFCPath)
            # arcpy.AddMessage(outputFC)
            #validate join between table and pu grid
            arcpy.AddMessage("Validating join... ")
            arcpy.management.ValidateJoin(outputFC, "UNIT_ID", table,"UNIT_ID")
            arcpy.AddMessage(arcpy.GetMessages())
            
            #join the table to the grid using joinField
            arcpy.management.JoinField(outputFC, "UNIT_ID", table, "UNIT_ID")
            arcpy.AddMessage("Output feature class: "+ str(outputFC))
            
        return