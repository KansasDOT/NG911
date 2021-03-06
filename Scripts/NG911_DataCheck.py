#-------------------------------------------------------------------------------
# Name: NG911_DataCheck
# Purpose: Collection of functions to check submitted NG911 data
#
# Author: Kristen Jordan, Kansas Data Access and Support Center
# kristen@kgs.ku.edu
#
# Created: 19/09/2014
# Modified: 31/10/2014 by dirktall04
# Changes include: Adding the currentPathSettings variable from
# NG911_Config as the default variable passed to several Data
# Check functions, modifications to the functions to allow
# them to use that variable as a data source.
#Modified: 02/04/2014 by Kristen
#Changes include: modifying format so the checks work with the 1.1 template
#-------------------------------------------------------------------------------


from arcpy import (AddField_management, AddMessage, CalculateField_management,  CopyRows_management, CreateAddressLocator_geocoding,
                   CreateTable_management, Delete_management, Exists, GeocodeAddresses_geocoding, GetCount_management, FieldInfo,
                   ListFields, MakeFeatureLayer_management, MakeTableView_management, SelectLayerByAttribute_management, Statistics_analysis,
                   SelectLayerByLocation_management, RebuildAddressLocator_geocoding, DeleteRows_management, GetInstallInfo, env)
from arcpy.da import Walk, InsertCursor, ListDomains, SearchCursor

from os import path
from os.path import basename, dirname, join

from time import strftime


def getCurrentLayerList(esb):
    layerList = ["RoadAlias", "AddressPoints", "RoadCenterline", "AuthoritativeBoundary", "CountyBoundary", "ESZ", "PSAP", "MunicipalBoundary"]
    for e in esb:
        layerList.append(e)
    return layerList


def userMessage(msg):
    print msg
    AddMessage(msg)


def getCurrentDomainList(version):
    domainList = ["AddressNumbers", "AddressParity", "AgencyID", "Counties", "Country",
                    "ESBType", "Municipality", "OneWay", "PlaceType", "PointLocation", "PostalCodes",
                    "PostalCommunities", "RoadClass", "RoadDirectionals", "RoadModifier", "RoadStatus",
                    "RoadSurface", "RoadTypes", "States", "Stewards", "Exception", "Submit"]
    #or get domain list from approved source

    if version == "10":
        domainList.remove("Exception")
        domainList.remove("Submit")

    return domainList


def fieldsWithDomains(version):
    #list of all the fields that have a domain
    fieldList = ["LOCTYPE", "STATUS", "SURFACE", "STEWARD", "AGENCYID","PLC", "RDCLASS", "PARITY", "ONEWAY", "MUNI", "COUNTY", "COUNTRY","PRD", "ZIP", "POSTCO", "STATE", "STS", "EXCEPTION", "SUBMIT"]

    if version == "10":
        fieldList.remove("EXCEPTION")
        fieldList.remove("SUBMIT")

    return fieldList

def getUniqueIDField(layer):
    id_dict = {"ADDRESSPOINTS":"ADDID", "AUTHORITATIVEBOUNDARY":"ABID", "COUNTYBOUNDARY":"CountyID", "ESB":"ESBID", "ESZ":"ESZID", "MUNICIPALBOUNDARY":"MUNI_ID", "PSAP":"ESBID", "ROADCENTERLINE":"SEGID", "ROADALIAS":"ALIASID"}
    try:
        id1 = id_dict[layer]
    except:
        id1 = ""
    return id1

def getDomainKeyword(domainName):
    ucase_list = ["AgencyID", "Country", "OneWay"]
    if domainName == "AddressParity":
        keyword = "PARITY"
    elif domainName == "Counties":
        keyword = "COUNTY"
    elif domainName == "ESBType":
        keyword = ""
    elif domainName == "Municipality":
        keyword = "MUNI"
    elif domainName == "PlaceType":
        keyword = "PLC"
    elif domainName == "PointLocation":
        keyword = "LOCTYPE"
    elif domainName == "PostalCodes":
        keyword = "ZIP"
    elif domainName == "PostalCommunities":
        keyword = "POSTCO"
    elif domainName == "RoadClass":
        keyword = "RDClass"
    elif domainName == "RoadDirectionals":
        keyword = "PRD"
    elif domainName == "RoadModifier":
        keyword = ""
    elif domainName == "RoadStatus":
        keyword = "STATUS"
    elif domainName == "RoadSurface":
        keyword = "SURFACE"
    elif domainName == "RoadTypes":
        keyword = "STS"
    elif domainName == "States":
        keyword = "STATE"
    elif domainName == "Stewards":
        keyword = "STEWARD"
    elif domainName in ucase_list:
        keyword = domainName.upper()

    return keyword


def getAddFieldInfo(table):
    lyr = basename(table)
    #field info
    if lyr == "TemplateCheckResults":
        fieldInfo = [(table, "DateFlagged", "DATE", "", "", ""),(table, "Description", "TEXT", "", "", 250),(table, "Category", "TEXT", "", "", 25)]
    elif lyr == "FieldValuesCheckResults":
        fieldInfo = [(table, "DateFlagged", "DATE", "", "", ""),(table, "Description", "TEXT", "", "", 250),(table, "Layer", "TEXT", "", "", 25),(table, "Field", "TEXT", "", "", 25),(table, "FeatureID", "TEXT", "", "", 38)]

    return fieldInfo


def getResultsFieldList(table):
    #get field info
    fieldInfo = getAddFieldInfo(table)
    fieldList = []
    #loop through added fields
    for fi in fieldInfo:
        #append the field name
        fieldList.append(fi[1])

    return fieldList


def RecordResults(resultType, values, gdb): # Guessed on whitespace formatting here. -- DT
    if resultType == "template":
        tbl = "TemplateCheckResults"
    elif resultType == "fieldValues":
        tbl = "FieldValuesCheckResults"

    table = join(gdb, tbl)
    fieldList = []

    if not Exists(table):
        CreateTable_management(gdb, tbl)
        fieldInfo = getAddFieldInfo(table)

        for fi in fieldInfo:
            #add field with desired parameters
            AddField_management(fi[0],fi[1],fi[2],fi[3],fi[4],fi[5])
            #populate field list
            fieldList.append(fi[1])

    if fieldList == []:
        fieldList = getResultsFieldList(table)

    cursor = InsertCursor(table, fieldList)
    for row in values:
        try:
            cursor.insertRow(row)
        except:
            userMessage(row)
    del cursor

def geocodeAddressPoints(pathsInfoObject):
    gdb = pathsInfoObject.gdbPath

    env.workspace = gdb
    addressPointPath = "AddressPoints"
    streetPath = "RoadCenterline"
    roadAliasPath = "RoadAlias"

    userMessage("Geocoding address points...")

    gc_table = "GeocodeTable"
    sl_field = "SingleLineInput"
    Locator = "Locator"
    addyview = "addy_view"
    output = "gc_test"

    # Get the fields from the input
    fields = ListFields(addressPointPath)

    # Create a fieldinfo object
    fieldinfo = FieldInfo()

    # Iterate through the fields and set them to fieldinfo
    for field in fields:
        if field.name in ("LABEL", "ZIP"):
            fieldinfo.addField(field.name, field.name, "VISIBLE", "")
    else:
        fieldinfo.addField(field.name, field.name, "HIDDEN", "")

    userMessage("Preparing addresses...")
    # The created addyview layer will have fields as set in fieldinfo object
    MakeTableView_management(addressPointPath, addyview, "", "", fieldinfo)

    # To persist the layer on disk make a copy of the view
    if Exists(gc_table):
        try:
            Delete_management(gc_table)
        except:
            userMessage("Please manually delete the table called gc_table and then run the geocoding again")

    if not Exists(gc_table):
        CopyRows_management(addyview, gc_table)

        #add single line input field for geocoding
        AddField_management(gc_table, sl_field, "TEXT", "", "", 250)

        #calculate field
        exp = '[LABEL] & " " & [ZIP]'
        CalculateField_management(gc_table, sl_field, exp, "VB")

        #generate locator
        fieldMap = """'Primary Table:Feature ID' <None> VISIBLE NONE;'*Primary Table:From Left' RoadCenterline:L_F_ADD VISIBLE NONE;
        '*Primary Table:To Left' RoadCenterline:L_T_ADD VISIBLE NONE;'*Primary Table:From Right' RoadCenterline:R_F_ADD VISIBLE NONE;
        '*Primary Table:To Right' RoadCenterline:R_T_ADD VISIBLE NONE;'Primary Table:Prefix Direction' RoadCenterline:PRD VISIBLE NONE;
        'Primary Table:Prefix Type' RoadCenterline:STP VISIBLE NONE;'*Primary Table:Street Name' RoadCenterline:RD VISIBLE NONE;
        'Primary Table:Suffix Type' RoadCenterline:STS VISIBLE NONE;'Primary Table:Suffix Direction' RoadCenterline:POD VISIBLE NONE;
        'Primary Table:Left City or Place' RoadCenterline:MUNI_L VISIBLE NONE;
        'Primary Table:Right City or Place' RoadCenterline:MUNI_R VISIBLE NONE;
        'Primary Table:Left ZIP Code' RoadCenterline:ZIP_L VISIBLE NONE;'Primary Table:Right ZIP Code' RoadCenterline:ZIP_R VISIBLE NONE;
        'Primary Table:Left State' RoadCenterline:STATE_L VISIBLE NONE;'Primary Table:Right State' RoadCenterline:STATE_R VISIBLE NONE;
        'Primary Table:Left Street ID' <None> VISIBLE NONE;'Primary Table:Right Street ID' <None> VISIBLE NONE;
        'Primary Table:Min X value for extent' <None> VISIBLE NONE;'Primary Table:Max X value for extent' <None> VISIBLE NONE;
        'Primary Table:Min Y value for extent' <None> VISIBLE NONE;'Primary Table:Max Y value for extent' <None> VISIBLE NONE;
        'Primary Table:Left Additional Field' <None> VISIBLE NONE;'Primary Table:Right Additional Field' <None> VISIBLE NONE;
        'Primary Table:Altname JoinID' RoadCenterline:SEGID VISIBLE NONE;'*Alternate Name Table:JoinID' RoadAlias:SEGID VISIBLE NONE;
        'Alternate Name Table:Prefix Direction' RoadAlias:A_PRD VISIBLE NONE;'Alternate Name Table:Prefix Type' <None> VISIBLE NONE;
        'Alternate Name Table:Street Name' RoadAlias:A_RD VISIBLE NONE;'Alternate Name Table:Suffix Type' RoadAlias:A_STS VISIBLE NONE;
        'Alternate Name Table:Suffix Direction' RoadAlias:A_POD VISIBLE NONE"""

        userMessage("Creating address locator...")
        # Process: Create Address Locator
        if Exists(Locator):
            RebuildAddressLocator_geocoding(Locator)
        else:
            try:
                CreateAddressLocator_geocoding("US Address - Dual Ranges", streetPath + " 'Primary Table';" + roadAliasPath + " 'Alternate Name Table'", fieldMap, Locator, "")
            except:
                try:
                    fieldMap = """'Primary Table:Feature ID' <None> VISIBLE NONE;'*Primary Table:From Left' RoadCenterline:L_F_ADD VISIBLE NONE;
                    '*Primary Table:To Left' RoadCenterline:L_T_ADD VISIBLE NONE;'*Primary Table:From Right' RoadCenterline:R_F_ADD VISIBLE NONE;
                    '*Primary Table:To Right' RoadCenterline:R_T_ADD VISIBLE NONE;'Primary Table:Prefix Direction' RoadCenterline:PRD VISIBLE NONE;
                    'Primary Table:Prefix Type' RoadCenterline:STP VISIBLE NONE;'*Primary Table:Street Name' RoadCenterline:RD VISIBLE NONE;
                    'Primary Table:Suffix Type' RoadCenterline:STS VISIBLE NONE;'Primary Table:Suffix Direction' RoadCenterline:POD VISIBLE NONE;
                    'Primary Table:Left City or Place' RoadCenterline:MUNI_L VISIBLE NONE;
                    'Primary Table:Right City or Place' RoadCenterline:MUNI_R VISIBLE NONE;
                    'Primary Table:Left ZIP Code' RoadCenterline:ZIP_L VISIBLE NONE;'Primary Table:Right ZIP Code' RoadCenterline:ZIP_R VISIBLE NONE;
                    'Primary Table:Left State' RoadCenterline:STATE_L VISIBLE NONE;'Primary Table:Right State' RoadCenterline:STATE_R VISIBLE NONE;
                    'Primary Table:Left Street ID' <None> VISIBLE NONE;'Primary Table:Right Street ID' <None> VISIBLE NONE;
                    'Primary Table:Display X' <None> VISIBLE NONE;'Primary Table:Display Y' <None> VISIBLE NONE;
                    'Primary Table:Min X value for extent' <None> VISIBLE NONE;'Primary Table:Max X value for extent' <None> VISIBLE NONE;
                    'Primary Table:Min Y value for extent' <None> VISIBLE NONE;'Primary Table:Max Y value for extent' <None> VISIBLE NONE;
                    'Primary Table:Left Additional Field' <None> VISIBLE NONE;'Primary Table:Right Additional Field' <None> VISIBLE NONE;
                    'Primary Table:Altname JoinID' RoadCenterline:SEGID VISIBLE NONE;'*Alternate Name Table:JoinID' RoadAlias:SEGID VISIBLE NONE;
                    'Alternate Name Table:Prefix Direction' RoadAlias:A_PRD VISIBLE NONE;'Alternate Name Table:Prefix Type' <None> VISIBLE NONE;
                    'Alternate Name Table:Street Name' RoadAlias:A_RD VISIBLE NONE;'Alternate Name Table:Suffix Type' RoadAlias:A_STS VISIBLE NONE;
                    'Alternate Name Table:Suffix Direction' RoadAlias:A_POD VISIBLE NONE"""
                    CreateAddressLocator_geocoding("US Address - Dual Ranges", streetPath + " 'Primary Table';" + roadAliasPath + " 'Alternate Name Table'", fieldMap, Locator, "", "DISABLED")
                except Exception as E:
                    userMessage(Locator)
                    userMessage("Cannot create address locator. Please email kristen@kgs.ku.edu this error message: " + str(E))


        if Exists(Locator):
            userMessage("Geocoding addresses...")

            #geocode table address
            if Exists(output):
                Delete_management(output)

            i = 0

            #set up geocoding
            gc_fieldMap = "Street LABEL VISIBLE NONE;City MUNI VISIBLE NONE;State State VISIBLE NONE;ZIP ZIP VISIBLE NONE"

            #geocode addresses
            try:
                GeocodeAddresses_geocoding(gc_table, Locator, gc_fieldMap, output, "STATIC")
                i = 1
            except:
                gc_fieldMap = "Street LABEL VISIBLE NONE;City MUNI VISIBLE NONE;State State VISIBLE NONE"

                try:
                    GeocodeAddresses_geocoding(gc_table, Locator, gc_fieldMap, output, "STATIC")
                    i = 1
                except:
                    userMessage("Could not geocode address points")

            #report records that didn't geocode
            if i == 1:
                wc = "Status <> 'M'"
                lyr = "lyr"

                MakeFeatureLayer_management(output, lyr, wc)

                rStatus = GetCount_management(lyr)
                rCount = int(rStatus.getOutput(0))

                if rCount > 0:
                    #set up parameters to report records that didn't geocode
                    values = []
                    recordType = "fieldValues"
                    today = strftime("%m/%d/%y")
                    filename = "AddressPoints"

                    rfields = ("ADDID")
                    with SearchCursor(output, rfields, wc) as rRows:
                        for rRow in rRows:
                            fID = rRow[0]
                            report = str(fID) + " did not geocode against centerline"
                            val = (today, report, filename, "", fID)
                            values.append(val)

                    #report records
                    if values != []:
                        RecordResults(recordType, values, gdb)

                    userMessage("Completed geocoding with " + str(rCount) + " errors.")

                else:
                    #this means all the records geocoded
                    userMessage("All records geocoded successfully.")
                    try:
                        Delete_management(output)
                    except:
                        userMessage("Geocoding table could not be deleted")
        else:
            userMessage("Could not geocode addresses")

def checkUniqueIDFrequency(currentPathSettings):
    gdb = currentPathSettings.gdbPath
    esbList = currentPathSettings.esbList
    fcList = currentPathSettings.fcList

    layerList = []

    env.workspace = gdb
    table = "ESB_IDS"

    #create temp table of esbID's
    if esbList <> []:
        layerList = ["ESB_IDS"]

        if Exists(table):
            Delete_management(table)

        CreateTable_management(gdb, table)

        AddField_management(table, "ESBID", "TEXT", "", "", 38)
        AddField_management(table, "ESB_LYR", "TEXT", "", "", 15)

        esbFields = ("ESBID")

        #copy ID's & esb layer type into the table
        for esb in esbList:
            with SearchCursor(esb, esbFields) as rows:
                for row in rows:
                    cursor = InsertCursor(table, ('ESBID', 'ESB_LYR'))
                    cursor.insertRow((row[0], esb))

        try:
            #clean up
            del rows, row, cursor
        except:
            print "objects cannot be deleted, they don't exist"

    else:
        for fc in fcList:
            fc = basename(fc)
            layerList.append(fc)

    #loop through layers in the gdb that aren't esb & ESB_IDS
##    layers = getCurrentLayerList(esb)
##    layers.append("ESB_IDS")

    values = []
    recordType = "fieldValues"
    today = strftime("%m/%d/%y")

    for layer in layerList:
##        if layer not in esb:
        if layer != "ESB_IDS":
            #for each layer, get the unique ID field
            uniqueID = getUniqueIDField(layer.upper())

        else:
            #for esb layers, get the unique ID field
            uniqueID = "ESBID"

        Statistics_analysis(layer, layer + "_freq", [[uniqueID,"COUNT"]], uniqueID)

        #set parameters for the search cursor
        where_clause = "FREQUENCY > 1"
        fields = (uniqueID, "FREQUENCY")

        fl = "fl"

        MakeTableView_management(layer + "_freq", fl, where_clause)

        result = GetCount_management(fl)
        count = int(result.getOutput(0))

        if count > 0:

            #set a search cursor with just the unique ID field
            with SearchCursor(layer + "_freq", fields, where_clause) as rows2:
                stringESBReport = ""
                for row2 in rows2:
                    if layer == "ESB_IDS":
                        stringEsbInfo = []
                        wc2 = "ESBID = " + row2[0]
                        with SearchCursor("ESB_IDS", ("ESB_LYR"), wc2) as esbRows:
                            for esbRow in esbRows:
                                stringEsbInfo.append(esbRow[0])

                        stringESBReport = " and ".join(stringEsbInfo)
                    else:
                        lyr = layer

                    #report duplicate IDs
                    report = str(row2[0]) + " is a duplicate ID"
                    if stringESBReport != "":
                        report = report + " in " + stringESBReport
                    val = (today, report, lyr, uniqueID, row2[0])
                    values.append(val)

        Delete_management(layer + "_freq")
        Delete_management(fl)

    #report duplicate records
    if values != []:
        RecordResults(recordType, values, gdb)
        userMessage("Checked unique ID frequency. Results are in table FieldValuesCheckResults.")
    else:
        userMessage("All ID's are unique.")

    #if it exists, clean up table
    if Exists(table):
        Delete_management(table)

def checkFrequency(fc, freq, fields, gdb, version):
    fl = "fl"
    fl1 = "fl1"
    wc = "FREQUENCY > 1"

    #remove the frequency table if it exists already
    if Exists(freq):
        try:
            Delete_management(freq)
        except:
            userMessage("Please manually delete " + freq + " and then run the frequency check again")

    if not Exists(freq):
        try:
            #see if we're working with address points or roads, create a where clause
            filename = ""
            if freq == join(gdb, "AP_Freq"):
                filename = "AddressPoints"
                wc1 = "HNO <> 0"
            elif freq == join(gdb, "Road_Freq"):
                filename = "RoadCenterline"
                wc1 = "L_F_ADD <> 0 AND L_T_ADD <> 0 AND R_F_ADD <> 0 AND R_T_ADD <> 0"

            if version != "10":
                wc1 = wc1 + " AND SUBMIT = 'Y'"

            #run query on fc to make sure 0's are ignored
            MakeTableView_management(fc, fl1, wc1)

            #split field names
            fieldsList = fields.split(";")
            fieldCountList = []
            fl_fields = []
            for f in fieldsList:
                f = f.strip()
                fList = [f,"COUNT"]
                fieldCountList.append(fList)
                fl_fields.append(f)

            #run frequency analysis
            Statistics_analysis(fl1, freq, fieldCountList, fields)

            #make feature layer
            MakeTableView_management(freq, fl, wc)

            #get count of the results
            result = GetCount_management(fl)
            count = int(result.getOutput(0))

            if count > 0:

                #set up parameters to report duplicate records
                values = []
                recordType = "fieldValues"
                today = strftime("%m/%d/%y")

                #add information to FieldValuesCheckResults for all duplicates

                #get field count
                fCount = len(fl_fields)

                #get the unique ID field name
                id1 = getUniqueIDField(filename.upper())

                #run a search on the frequency table to report duplicate records
                with SearchCursor(freq, fl_fields, wc) as rows:
                    for row in rows:
                        i = 0
                        #generate where clause to find duplicate ID's
                        wc = ""
                        while i < fCount:
                            stuff = ""
                            if row[i] != None:
                                try:
                                    stuff = " = '" + row[i] + "' "
                                except:
                                    stuff = " = " + str(row[i]) + " "
                            else:
                                stuff = " is null "
                            wc = wc + fl_fields[i] + stuff + "and "
                            i += 1

                        #trim last "and " off where clause
                        wc = wc[0:-5]

                        #find records with duplicates to get their unique ID's
                        with SearchCursor(fl1, (id1), wc) as sRows:
                            for sRow in sRows:
                                fID = sRow[0]
                                report = str(fID) + " has duplicate field information"
                                val = (today, report, filename, "", fID)
                                values.append(val)

                #report duplicate records
                if values != []:
                    RecordResults(recordType, values, gdb)
                    userMessage("Checked frequency. Results are in table FieldValuesCheckResults")

            elif count == 0:
                userMessage("Checked frequency. All records are unique.")

            #clean up
            Delete_management(fl)
            Delete_management(fl1)

            try:
                Delete_management(freq)
            except:
                userMessage("Could not delete frequency table")
        except:
            userMessage("Could not fully run frequency check")

def checkLayerList(pathsInfoObject):
    gdb = pathsInfoObject.gdbPath
    esb = pathsInfoObject.esbList

    values = []
    today = strftime("%m/%d/%y")

    userMessage("Checking geodatabase layers...")
    #get current layer list
    layerList = getCurrentLayerList(esb)
    layers = []
    for dirpath, dirnames, filenames in Walk(gdb, True, '', False, ["Table","FeatureClass"]):
##        ignoreList = ("gc_test", "TemplateCheckResults", "FieldValuesCheckResults", "GeocodeTable")
        for fn in filenames:
            name = basename(fn)
            layers.append(name)

##    userMessage(layers)

    #report any required layers that are not present
    for l in layerList:
        if l not in layers:
            report = "Required layer " + l + " is not in geodatabase."
            userMessage(report)
            val = (today, report, "Layer")
            values.append(val)

    #record issues if any exist
    if values != []:
        RecordResults("template", values, gdb)


def getKeyword(layer, esb):
    if layer in esb:
        keyword = "EmergencyBoundary"
    else:
        keyword = layer

    return keyword


def getRequiredFields(folder, version):
    path1 = path.join(folder, "NG911_RequiredFields.txt")

    #create a field definition dictionary
    rfDict = {}

    #make sure file path exists
    if path.exists(path1):
        fieldDefDoc = open(path1, "r")

        #get the header information
        headerLine = fieldDefDoc.readline()
        valueList = headerLine.split("|")
        ## print valueList

        #get field indexes
        fcIndex = valueList.index("FeatureClass")
        fieldIndex = valueList.index("Field\n")

        #parse the text to populate the field definition dictionary
        for line in fieldDefDoc.readlines():
            stuffList = line.split("|")
            #set up values
            fc = stuffList[0]
            field = stuffList[1].rstrip()
            fieldList = []

            #see if field list already exists
            if fc in rfDict.iterkeys():
                fieldList = rfDict[fc]

            #append new value onto list
            fieldList.append(field)

            if version == "10":
                if "EXCEPTION" in fieldList:
                    fieldList.remove("EXCEPTION")
            #set value as list
            rfDict[fc] = fieldList
    else:
        userMessage("The file " + path1 + " is required to run field checks.")

    return rfDict


def getFieldDomain(field, folder):
##    userMessage(field)

    docPath = path.join(folder, field + "_Domains.txt")
    ## print docPath

    domainDict = {}

    #make sure path exists
    if path.exists(docPath):
        doc = open(docPath, "r")

        headerLine = doc.readline()
        valueList = headerLine.split("|")

        valueIndex = valueList.index("Values")
        defIndex = valueList.index("Definition\n")


        #parse the text to population the field definition dictionary
        for line in doc.readlines():
            if line != "\n":
                stuffList = line.split("|")
    ##            userMessage(stuffList)
                domainDict[stuffList[0].rstrip().lstrip()] = stuffList[1].rstrip().lstrip()

    else:
        userMessage("The file " + docPath + " is required to run a domain check.")

    return domainDict


def checkValuesAgainstDomain(pathsInfoObject):
    gdb = pathsInfoObject.gdbPath
    folder = pathsInfoObject.domainsFolderPath
    fcList = pathsInfoObject.fcList
    esb = pathsInfoObject.esbList
    version = pathsInfoObject.gdbVersion

    userMessage("Checking field values against approved domains...")
    #set up parameters to report duplicate records
    values = []
    resultType = "fieldValues"
    today = strftime("%m/%d/%y")
    filename = ""

    #set environment
    env.workspace = gdb

    #get list of fields with domains
    fieldsWDoms = fieldsWithDomains(version)

    for fullPath in fcList:
        fc = basename(fullPath).replace("'", "")
        layer = fc.upper()
        if fc in esb:
            layer = "ESB"

        id1 = getUniqueIDField(layer)
        if id1 != "":
            fields = []
            #create complete field list
            fields = ListFields(fc)
            fieldNames = []

            for field in fields:
                if field.name <> "MUNI_ID":
                    fieldNames.append((field.name).upper())

            #see if fields from complete list have domains
            for fieldName in fieldNames:
                if "_" in fieldName:
                    fieldN = fieldName.split("_")[0]
                else:
                    fieldN = fieldName

                userMessage(fieldN)
                #if field has a domain
                if fieldN in fieldsWDoms:

                    #get the full domain dictionary
                    domainDict = getFieldDomain(fieldN, folder)

                    if domainDict != {}:
                        #put domain values in a list
                        domainList = []

                        for val in domainDict.iterkeys():
                            domainList.append(val)

                        #add values for some CAD users of blank and space (edit suggested by Sherry M. & Keith S. Dec 2014)
                        domainList.append('')
                        domainList.append(" ")

                        #if the domain is counties, add county names to the list without "COUNTY" so both will work (edit suggest by Keith S. Dec 2014)
                        if fieldN == "COUNTY":
                            q = len(domainList)
                            i = 0
                            while i < q:
                                dl1 = domainList[i].split(" ")[0]
    ##                            userMessage(dl1)
                                domainList.append(dl1)
                                i += 1

                        #loop through records for that particular field to see if all values match domain
                        wc = fieldName + " is not null"
                        with SearchCursor(fullPath, (id1, fieldName), wc) as rows:
                            for row in rows:
                                if row[1] is not None:
                                    fID = row[0]
                                    #see if field domain is actually a range
                                    if fieldN == "HNO":
                                        hno = row[1]
                                        if hno > 999999 or hno < 0:
                                            report = "Value " + str(row[1]) + " not in approved domain for field " + fieldName
                                            val = (today, report, fc, fieldName, fID)
                                            values.append(val)
                                    #otherwise, compare row value to domain list
                                    else:
                                        if row[1] not in domainList:
                                            report = "Value " + str(row[1]) + " not in approved domain for field " + fieldName
                                            val = (today, report, fc, fieldName, fID)
                                            values.append(val)

                    else:
                        userMessage("Could not compare domain for " + fieldName)

    if values != []:
        RecordResults(resultType, values, gdb)

    userMessage("Completed checking fields against domains: " + str(len(values)) + " issues found")


def checkRequiredFieldValues(pathsInfoObject):
    gdb = pathsInfoObject.gdbPath
    folder = pathsInfoObject.domainsFolderPath
    esb = pathsInfoObject.esbList
    version = pathsInfoObject.gdbVersion

    userMessage("Checking that required fields have all values...")

    #get today's date
    today = strftime("%m/%d/%y")

    #get required fields
    rfDict = getRequiredFields(folder, version)

    if rfDict != {}:

        values = []

        #walk through the tables/feature classes
        for dirpath, dirnames, filenames in Walk(gdb, True, '', False, ["Table","FeatureClass"]):
            for filename in filenames:
                if filename.upper() not in ("FIELDVALUESCHECKRESULTS", "TEMPLATECHECKRESULTS"):
                    fullPath = path.join(gdb, filename)
                    if filename.upper() in esb:
                        layer = "ESB"
                    else:
                        layer = filename.upper()
                    id1 = getUniqueIDField(layer)
                    if id1 != "":

                        #get the keyword to acquire required field names
                        keyword = getKeyword(filename, esb)

                        #goal: get list of required fields that are present in the feature class
                        #get the appropriate required field list
                        if keyword in rfDict:
                            requiredFieldList = rfDict[keyword]

                        rfl = []
                        for rf in requiredFieldList:
                            rfl.append(rf.upper())

                        #get list of fields in the feature class
                        allFields = ListFields(fullPath)

                        #make list of field names
                        fields = []
                        for aF in allFields:
                            fields.append(aF.name.upper())

                        #convert lists to sets
                        set1 = set(rfl)
                        set2 = set(fields)

                        #get the set of fields that are the same
                        matchingFields = list(set1 & set2)

                        #only work with records that are for submission
                        lyr2 = "lyr2"
                        if version == "10":
                            MakeTableView_management(fullPath, lyr2)
                        else:
                            wc2 = "SUBMIT = 'Y'"
                            MakeTableView_management(fullPath, lyr2, wc2)

                        #create where clause to select any records where required values aren't populated
                        wc = ""

                        for field in matchingFields:
                            wc = wc + " " + field + " is null or "

                        wc = wc[0:-4]

                        #make table view using where clause
                        lyr = "lyr"
                        MakeTableView_management(lyr2, lyr, wc)

                        #get count of the results
                        result = GetCount_management(lyr)
                        count = int(result.getOutput(0))


                        #if count is greater than 0, it means a required value somewhere isn't filled in
                        if count > 0:
                            #make sure the objectID gets included in the search for reporting
                            if id1 not in matchingFields:
                                matchingFields.append(id1)

                            #run a search cursor to get any/all records where a required field value is null
                            with SearchCursor(fullPath, (matchingFields), wc) as rows:
                                for row in rows:
                                    k = 0
                                    #get object ID of the field
                                    oid = str(row[matchingFields.index(id1)])

                                    #loop through row
                                    while k < len(matchingFields):
                                        #see if the value is nothing
                                        if row[k] is None:
                                            #report the value if it is indeed null
                                            report = matchingFields[k] + " is null for Feature ID " + oid
                                            userMessage(report)
                                            val = (today, report, filename, matchingFields[k], oid)
                                            values.append(val)

                                        #iterate!
                                        k = k + 1
                        else:
                            userMessage( "All required values present for " + filename)

                        Delete_management(lyr)
                        Delete_management(lyr2)

        if values != []:
            RecordResults("fieldValues", values, gdb)

        userMessage("Completed check for required field values: " + str(len(values)) + " issues found")

    else:
        userMessage("Could not check required field values")


def checkRequiredFields(pathsInfoObject):
    gdb = pathsInfoObject.gdbPath
    folder = pathsInfoObject.domainsFolderPath
    esb = pathsInfoObject.esbList
    version = pathsInfoObject.gdbVersion

    userMessage("Checking that required fields exist...")

    #get today's date
    today = strftime("%m/%d/%y")
    values = []

    #get required fields
    rfDict = getRequiredFields(folder, version)

    if rfDict != {}:

        #walk through the tables/feature classes
        for dirpath, dirnames, filenames in Walk(gdb, True, '', False, ["Table","FeatureClass"]):
            for filename in filenames:
                fields = []
                fullPath = path.join(gdb, filename)

                #list fields
                fs = ListFields(fullPath)

                for f in fs:
                    fields.append(f.name.upper())

                #get the keyword to acquire required field names
                keyword = getKeyword(filename, esb)

                #get the appropriate comparison list
                if keyword in rfDict:
                    comparisonList = rfDict[keyword]
                    ## print comparisonList

                    #loop through required fields to make sure they exist in the geodatabase
                    for comparisonField in comparisonList:
                        if comparisonField.upper() not in fields:
                            report = filename + " does not have required field " + comparisonField
                            userMessage(report)
                            #add issue to list of values
                            val = (today, report, "Field")
                            values.append(val)

        #record issues if any exist
        if values != []:
            RecordResults("template", values, gdb)

        userMessage("Completed check for required fields: " + str(len(values)) + " issues found")

    else:
        userMessage("Could not check for required fields.")


def checkFeatureLocations(pathsInfoObject):
    gdb = pathsInfoObject.gdbPath
    fcList = pathsInfoObject.fcList
    esb = pathsInfoObject.esbList
    version = pathsInfoObject.gdbVersion

    RoadAlias = join(gdb, "RoadAlias")

    if RoadAlias in fcList:
        fcList.remove(RoadAlias)

    userMessage("Checking feature locations...")

    #get today's date
    today = strftime("%m/%d/%y")
    values = []

    #make sure features are all inside authoritative boundary

    #get authoritative boundary
    authBound = path.join(gdb, "NG911", "AuthoritativeBoundary")
    ab = "ab"

    MakeFeatureLayer_management(authBound, ab)

    for fullPath in fcList:
        fl = "fl"
        if version == "10":
            MakeFeatureLayer_management(fullPath, fl)
        else:
            if "RoadCenterline" in fullPath:
                wc = "SUBMIT = 'Y' AND EXCEPTION not in ('EXCEPTION INSIDE', 'EXCEPTION BOTH')"
            else:
                wc = "SUBMIT = 'Y'"
            MakeFeatureLayer_management(fullPath, fl, wc)

        try:

            #select by location to get count of features outside the authoritative boundary
            SelectLayerByLocation_management(fl, "WITHIN", ab)
            SelectLayerByAttribute_management(fl, "SWITCH_SELECTION", "")
            #get count of selected records
            result = GetCount_management(fl)
            count = int(result.getOutput(0))

            #report results
            if count > 0:
                layer = basename(fullPath)
                if layer in esb:
                    layerName = "ESB"
                else:
                    layerName = layer
                id1 = getUniqueIDField(layerName.upper())
                report = "Feature not inside authoritative boundary"
                if id1 != '':
                    with SearchCursor(fl, (id1)) as rows:
                        for row in rows:
                            fID = row[0]
                            val = (today, report, layer, " ", fID)
                            values.append(val)
                else:
                    userMessage("Could not process features in " + fullPath)
            else:
                userMessage( fullPath + ": all records inside authoritative boundary")
        except:
            userMessage("Could not check locations of " + fullPath)

        finally:

            #clean up
            Delete_management(fl)

    if values != []:
        RecordResults("fieldValues", values, gdb)


    userMessage("Completed check on feature locations: " + str(len(values)) + " issues found")


def main_check(checkType, currentPathSettings):
##    try:
##        from NG911_Config import currentPathSettings # currentPathSettings should have all the path information available. ## import esb, gdb, folder
##    except:
##        userMessage( "Copy config file into command line")

    checkList = currentPathSettings.checkList

    #check geodatabase template
    if checkType == "template":
        if checkList[0] == "true":
            checkLayerList(currentPathSettings)

        if checkList[1] == "true":
            checkRequiredFields(currentPathSettings)

        if checkList[2] == "true":
            checkRequiredFieldValues(currentPathSettings)

    #check address points
    elif checkType == "AddressPoints":
        if checkList[0] == "true":
            checkValuesAgainstDomain(currentPathSettings)

        if checkList[1] == "true":
            checkFeatureLocations(currentPathSettings)

        if checkList[2] == "true":
            geocodeAddressPoints(currentPathSettings)

        if checkList[3] == "true":
            addressPoints = join(currentPathSettings.gdbPath, "AddressPoints")
            AP_freq = join(currentPathSettings.gdbPath, "AP_Freq")
            AP_fields = "MUNI;HNO;HNS;PRD;STP;RD;STS;POD;POM;ZIP;BLD;FLR;UNIT;ROOM;SEAT;LOC;LOCTYPE"
            checkFrequency(addressPoints, AP_freq, AP_fields, currentPathSettings.gdbPath, currentPathSettings.gdbVersion)

        if checkList[4] == "true":
            checkUniqueIDFrequency(currentPathSettings)

    #check roads
    elif checkType == "Roads":
        if checkList[0] == "true":
            checkValuesAgainstDomain(currentPathSettings)

        if checkList[1] == "true":
            checkFeatureLocations(currentPathSettings)

        if checkList[2] == "true":
            roads = join(currentPathSettings.gdbPath, "RoadCenterline")
            road_freq = join(currentPathSettings.gdbPath, "Road_Freq")
            road_fields = """STATE_L;STATE_R;COUNTY_L;COUNTY_R;MUNI_L;MUNI_R;L_F_ADD;L_T_ADD;R_F_ADD;R_T_ADD;
            PARITY_L;PARITY_R;POSTCO_L;POSTCO_R;ZIP_L;ZIP_R;ESN_L;ESN_R;MSAGCO_L;MSAGCO_R;PRD;STP;RD;STS;POD;
            POM;SPDLIMIT;ONEWAY;RDCLASS;LABEL;ELEV_F;ELEV_T;ESN_C;SURFACE;STATUS;TRAVEL;LRSKEY"""
            checkFrequency(roads, road_freq, road_fields, currentPathSettings.gdbPath, currentPathSettings.gdbVersion)

        if checkList[3] == "true":
            checkUniqueIDFrequency(currentPathSettings)

    #check boundaries or ESB
    elif checkType in ("admin", "ESB"):
        if checkList[0] == "true":
            checkValuesAgainstDomain(currentPathSettings)

        if checkList[1] == "true":
            checkFeatureLocations(currentPathSettings)

        if checkList[2] == "true":
            checkUniqueIDFrequency(currentPathSettings)


if __name__ == '__main__':
    main()
