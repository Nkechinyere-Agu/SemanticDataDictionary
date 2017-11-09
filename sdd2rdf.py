import urllib2
import csv
import sys
import re
from datetime import datetime
import time
import pandas as pd

kb=":"
out_fn = "out.ttl"
prefix_fn="prefixes.txt"

studyRef = None

# Need to implement input flags rather than ordering
if (len(sys.argv) < 2) :
    print "Usage: python sdd2rdf.py <SDD_file> [<data_file>] [<codebook_file>] [<output_file>] [kb_prefix]\nOptional arguments can be skipped by entering '!'"
    sys.exit(1)

if (len(sys.argv) > 1) :
    sdd_fn = sys.argv[1]

    if (len(sys.argv) > 2) :
        data_fn = sys.argv[2]

        if (len(sys.argv) > 3) :
            cb_fn = sys.argv[3]
            if (len(sys.argv) > 4) :
                out_fn = sys.argv[4]
                if (len(sys.argv) > 5) :
                    if not (sys.argv[5] == "!" ):
                        if ":" not in sys.argv[5] :
                            kb = sys.argv[5] + ":"
                        else :                       
                            kb = sys.argv[5]
        else :
            cb_fn = raw_input("If you wish to use a Codebook file, please type the path and press 'Enter'.\n Otherwise, type '!' and press Enter: ")       
    else : 
        data_fn = raw_input("If you wish to use a Data file, please type the path and press 'Enter'.\n Otherwise, type '!' and press Enter: ")
        cb_fn = raw_input("If you wish to use a Codebook file, please type the path and press 'Enter'.\n Otherwise, type '!' and press Enter: ")

if cb_fn == "!" :
    cb_fn = None

if data_fn == "!" :
    data_fn = None

if out_fn == "!" :
    out_fn = "out.ttl"

output_file = open(out_fn,"w")
prefix_file = open(prefix_fn,"r")
prefixes = prefix_file.readlines()

for prefix in prefixes :
    output_file.write(prefix)
output_file.write("\n")

# K: parameterize this, too?
code_mappings_url = 'https://raw.githubusercontent.com/tetherless-world/chear-ontology/master/code_mappings.csv'
#code_mappings_response = urllib2.urlopen(code_mappings_url)
code_mappings_reader = pd.read_csv(code_mappings_url)

column_ind = None
attr_ind = None
attr_of_ind = None
entity_ind = None
unit_ind = None
time_ind = None
role_ind = None
relation_ind = None
relation_to_ind = None
derived_from_ind = None
generated_by_ind = None
position_ind = None
label_ind = None
comment_ind = None

sdd_key = None
cb_key = None
data_key = None

unit_code_list = []
unit_uri_list = []
unit_label_list = []

actual_list = []
virtual_list = []

actual_tuples = []
virtual_tuples = []
cb_tuple = {}

try :
    sdd_file = pd.read_csv(sdd_fn)
except:
    print "Error: The specified SDD file does not exist."
    sys.exit(1)

try: 
    # Set virtual and actual columns
    for row in sdd_file.itertuples() :
	if (pd.isnull(row.Column)) :
		print "Error: The SDD must have a column named 'Column'"
		sys.exit(1)
        if row.Column.startswith("??") :
		virtual_list.append(row)
        else :
		actual_list.append(row)
except : 
    print "Something went wrong when trying to read the SDD"
    sys.exit(1)

#Using itertuples on a data frame makes the column heads case-sensitive
for code_row in code_mappings_reader.itertuples() :
    if pd.notnull(code_row.code):
	unit_code_list.append(code_row.code)
    if pd.notnull(code_row.uri):
	unit_uri_list.append(code_row.uri)
    if pd.notnull(code_row.label):
	unit_label_list.append(code_row.label)

def codeMapper(input_word) :
    unitVal = input_word
    for unit_label in unit_label_list :
        if (unit_label == input_word) :
            unit_index = unit_label_list.index(unit_label)
            unitVal = unit_uri_list[unit_index]
    for unit_code in unit_code_list :
        if (unit_code == input_word) :
            unit_index = unit_code_list.index(unit_code)
            unitVal = unit_uri_list[unit_index]
    return unitVal    

def convertVirtualToKGEntry(*args) :
    if (args[0][:2] == "??") :
        if (studyRef is not None ) :
            if (args[0]==studyRef) :
                return kb + args[0][2:]
        if (len(args) == 2) :
            return kb + args[0][2:] + "-" + args[1]
        else : 
            return kb + args[0][2:]
    elif (':' not in args[0]) :
        # Need to implement check for entry in column list
        return '"' + args[0] + "\"^^xsd:string"
    else :
        return args[0]

def checkVirtual(input_word) :
    try:
        if (input_word[:2] == "??") :
            return True
        else :
            return False
    except :
        print "Something went wrong in checkVirtual()"
        sys.exit(1)


def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

#virtual_list is a list of tuples
def writeVirtualRDF(virtual_list, virtual_tuples, output_file) :
    #output_file.write(kb + "head-" + item[column_ind][2:] + " { "
    assertionString = ''
    provenanceString = ''
    output_file.write(kb + "head-virtual_entry { ")
    output_file.write("\n\t" + kb + "nanoPub-virtual_entry\trdf:type np:Nanopublication")
    output_file.write(" ;\n\t\tnp:hasAssertion " + kb + "assertion-virtual_entry")
    output_file.write(" ;\n\t\tnp:hasProvenance " + kb + "provenance-virtual_entry")
    output_file.write(" ;\n\t\tnp:hasPublicationInfo " + kb + "pubInfo-virtual_entry")
    output_file.write(" .\n}\n\n")
    for item in virtual_list :
        virtual_tuple = {}
        assertionString += "\n\t" + kb + item.Column[2:] + "\trdf:type\towl:Class"
        assertionString += " ;\n\t\trdfs:label \"" + item.Column[2:] + "\""
        # Set the rdf:type of the virtual row to either the Attribute or Entity value (or else owl:Individual)
        if (pd.notnull(item.Entity)) and (pd.isnull(item.Attribute)) :
	    assertionString += " ;\n\t\trdfs:subClassOf " + codeMapper(item.Entity)
            virtual_tuple["Column"]=item.Column
            virtual_tuple["Entity"]=codeMapper(item.Entity)
            if (virtual_tuple["Entity"] == "hasco:Study") :
                global studyRef
                studyRef = item.Column
                virtual_tuple["Study"] = item.Column
        elif (pd.notnull(item.Entity)) and (pd.notnull(item.Attribute)) :
            assertionString += " ;\n\t\trdfs:subClassOf " + codeMapper(item.Attribute)
            virtual_tuple["Column"]=item.Column
            virtual_tuple["Attribute"]=codeMapper(item.Attribute)
        else :
            print "Warning: Virtual column not assigned an Entity or Attribute value, or was assigned both."
            virtual_tuple["Column"]=item.Column
        
        # If there is a value in the inRelationTo column ...
        if (pd.notnull(item.inRelationTo)) :
            virtual_tuple["inRelationTo"]=item.inRelationTo
            # If there is a value in the Relation column but not the Role column ...
            if (pd.notnull(item.Relation)) and (pd.isnull(item.Role)) :
		assertionString += " ;\n\t\t" + item.Relation + " " + convertVirtualToKGEntry(item.inRelationTo)
                virtual_tuple["Relation"]=item.Relation
            # If there is a value in the Role column but not the Relation column ...
            elif (pd.isnull(item.Relation)) and (pd.notnull(item.Role)) :
                assertionString += " ;\n\t\tsio:hasRole [ rdf:type\t" + item.Role + " ;\n\t\t\tsio:inRelationTo " + convertVirtualToKGEntry(item.inRelationTo) + " ]"
                virtual_tuple["Role"]=item.Role
            # If there is a value in the Role and Relation columns ...
            elif (pd.notnull(item.Relation)) and (pd.notnull(item.Role)) :
                virtual_tuple["Relation"]=item.Relation
                virtual_tuple["Role"]=item.Role
                assertionString += " ;\n\t\tsio:inRelationTo " + convertVirtualToKGEntry(item.inRelationTo) 
        assertionString += " .\n"
        #output_file.write(" .\n}\n\n")
        # Nanopublication provenance
        #output_file.write(kb + "provenance-" + item[column_ind][2:] + " { ")
        provenanceString += "\n\t" + kb + item.Column[2:] 
        provenanceString +="\n\t\tprov:generatedAtTime\t\"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime "
        if (pd.notnull(item.wasDerivedFrom)) :
            provenanceString += " ;\n\t\tprov:wasDerivedFrom " + convertVirtualToKGEntry(item.wasDerivedFrom)
            virtual_tuple["wasDerivedFrom"]=item.wasDerivedFrom
        if (pd.notnull(item.wasGeneratedBy)) :
            provenanceString += " ;\n\t\tprov:wasGeneratedBy " + convertVirtualToKGEntry(item.wasGeneratedBy)
            virtual_tuple["wasGeneratedBy"]=item.wasGeneratedBy
        provenanceString += " .\n"
        virtual_tuples.append(virtual_tuple)
    output_file.write(kb + "assertion-virtual_entry {")
    output_file.write(assertionString + "\n}\n\n")
    output_file.write(kb + "provenance-virtual_entry {")
    provenanceString = "\n\t" + kb + "assertion-virtual_entry\tprov:generatedAtTime\t\"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime .\n" + provenanceString
    output_file.write(provenanceString + "\n}\n\n")
    output_file.write(kb + "pubInfo-virtual_entry {\n\t" + kb + "nanoPub-virtual_entry\tprov:generatedAtTime\t\"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime .\n}\n\n")

def writeActualRDF(actual_list, actual_tuples, output_file) :
    assertionString = ''
    provenanceString = ''
    publicationInfoString = ''
    output_file.write(kb + "head-actual_entry { ")
    output_file.write("\n\t" + kb + "nanoPub-actual_entry\trdf:type np:Nanopublication")
    output_file.write(" ;\n\t\tnp:hasAssertion " + kb + "assertion-actual_entry")
    output_file.write(" ;\n\t\tnp:hasProvenance " + kb + "provenance-actual_entry")
    output_file.write(" ;\n\t\tnp:hasPublicationInfo " + kb + "pubInfo-actual_entry")
    output_file.write(" .\n}\n\n")
    for item in actual_list :
        actual_tuple = {}
        assertionString += "\n\t" + kb + item.Column.replace(" ","_") + "\trdf:type\towl:Class"
        #output_file.write(" ;\n\trdfs:label \"" + item[column_ind] + "\"")
        if (pd.notnull(item.Attribute)) :
            assertionString += " ;\n\t\trdfs:subClassOf " + convertVirtualToKGEntry(codeMapper(item.Attribute))
            actual_tuple["Column"]=item.Column
            actual_tuple["Attribute"]=codeMapper(item.Attribute)
        else :
            assertionString += " ;\n\t\trdfs:subClassOf " + convertVirtualToKGEntry(codeMapper("sio:Attribute"))
            actual_tuple["Column"]=item.Column
            actual_tuple["Attribute"]=codeMapper("sio:Attribute")
            print "WARN: Actual column not assigned an Attribute value."
            #sys.exit(1)
            #output_file.write(kb + item[column_ind] + " a owl:Individual")
        if (pd.notnull(item.attributeOf)) :
            assertionString += " ;\n\t\tsio:isAttributeOf " + convertVirtualToKGEntry(item.attributeOf)
            actual_tuple["isAttributeOf"]=item.attributeOf
        else :
	    print "WARN: Actual column not assigned an isAttributeOf value. Skipping...."
	    assertionString += " ;\n\n"
            #print "Error: Actual column not assigned an isAttributeOf value."
            #sys.exit(1)
        if (pd.notnull(item.Unit)) :
            assertionString += " ;\n\t\tsio:hasUnit " + codeMapper(item.Unit)
            actual_tuple["Unit"] = codeMapper(item.Unit)
        if (pd.notnull(item.Time)) :
            assertionString += " ;\n\t\tsio:existsAt " + convertVirtualToKGEntry(item.Time)
            actual_tuple["Time"]=item.Time
        if (pd.notnull(item.inRelationTo)) :
            assertionString += " ;\n\t\tsio:inRelationTo " + convertVirtualToKGEntry(item.inRelationTo)
            actual_tuple["inRelationTo"]=item.inRelationTo
        if (pd.notnull(item.Relation) and pd.notnull(item.inRelationTo)) :
            assertionString += " ;\n\t\t" + item.Relation + " " + convertVirtualToKGEntry(item.inRelationTo)
            actual_tuple["Relation"]=item.Relation
        if (pd.notnull(item.Label)) :
            assertionString += " ;\n\t\trdfs:label \"" + item.Label + "\"^^xsd:String" 
            actual_tuple["Label"]=item.Label
        if (pd.notnull(item.Comment)) :
            assertionString += " ;\n\t\trdfs:comment \"" + item.Comment + "\"^^xsd:String"
            actual_tuple["Comment"]=item.Comment
        assertionString += " .\n" 
        provenanceString += "\n\t" + kb + item.Column.replace(" ","_")
        provenanceString += "\n\t\tprov:generatedAtTime \"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime "
        if (pd.notnull(item.wasDerivedFrom)) :
            provenanceString += " ;\n\t\tprov:wasDerivedFrom " + convertVirtualToKGEntry(item.wasDerivedFrom)
            actual_tuple["wasDerivedFrom"]=item.wasDerivedFrom
        if (pd.notnull(item.wasGeneratedBy)) :
            provenanceString += " ;\n\t\tprov:wasGeneratedBy " + convertVirtualToKGEntry(item.wasGeneratedBy)
            actual_tuple["wasGeneratedBy"]=item.wasGeneratedBy
        provenanceString += " .\n"
        if (pd.notnull(item.hasPosition)) :
            publicationInfoString += "\n\t" + kb + item.Column.replace(" ","_") + "\thasco:hasPosition\t\"" + item.hasPosition + "\"^^xsd:integer ."
            actual_tuple["hasPosition"]=item.hasPosition
        #output_file.write(" .\n}\n\n")
        actual_tuples.append(actual_tuple)
    output_file.write(kb + "assertion-actual_entry {")
    output_file.write(assertionString + "\n}\n\n")
    output_file.write(kb + "provenance-actual_entry {")
    provenanceString = "\n\t" + kb + "assertion-actual_entry\tprov:generatedAtTime\t\"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime .\n" + provenanceString
    output_file.write(provenanceString + "\n}\n\n")
    output_file.write(kb + "pubInfo-actual_entry {\n\t" + kb + "nanoPub-actual_entry\tprov:generatedAtTime\t\"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime .")
    output_file.write(publicationInfoString + "\n}\n\n")

def writeVirtualEntry(assertionString,provenanceString,publicationInfoString, v_column, index) : 
    try :
        for v_tuple in virtual_tuples :
            if (v_tuple["Column"] == v_column) :
                if "Study" in v_tuple :
                    #print "Got to Study\n"
                    continue
                else :
                    assertionString += "\n\t" + kb + v_tuple["Column"][2:] + "-" + index + "\trdf:type\t" + kb + v_tuple["Column"][2:]
                    if "Entity" in v_tuple :
                        assertionString += ";\n\t\trdf:type\t" + v_tuple["Entity"]
                    if "Attribute" in v_tuple :
                        assertionString += ";\n\t\trdf:type\t" + v_tuple["Attribute"]
                    if "Subject" in v_tuple :
                        assertionString += ";\n\t\tsio:hasIdentifier " + kb + v_tuple["Subject"] + "-" + index
                    if "inRelationTo" in v_tuple :
                        if ("Role" in v_tuple) and ("Relation" not in v_tuple) :
                            assertionString += " ;\n\t\tsio:hasRole [ rdf:type\t" + v_tuple["Role"] + " ;\n\t\t\tsio:inRelationTo " + convertVirtualToKGEntry(v_tuple["inRelationTo"], index) + " ]"
                        elif ("Role" not in v_tuple) and ("Relation" in v_tuple) :
                            assertionString += " ;\n\t\t" + v_tuple["Relation"] + " " + convertVirtualToKGEntry(v_tuple["inRelationTo"],index)
                        elif ("Role" not in v_tuple) and ("Relation" not in v_tuple) :
                            assertionString += " ;\n\t\tsio:inRelationTo " + convertVirtualToKGEntry(v_tuple["inRelationTo"],index)
                    assertionString += " .\n"
                    if "wasGeneratedBy" in v_tuple : 
                        provenanceString += " ;\n\t\tprov:wasGeneratedBy " + convertVirtualToKGEntry(v_tuple["wasGeneratedBy"],index)
                    if "wasDerivedFrom" in v_tuple : 
                        provenanceString += " ;\n\t\tprov:wasDerivedFrom " + convertVirtualToKGEntry(v_tuple["wasDerivedFrom"],index)
                    if not provenanceString is "" :
                        provenanceString += " .\n"
                    if ("wasGeneratedBy" in v_tuple ) and (checkVirtual(v_tuple["wasGeneratedBy"])) :
                        writeVirtualEntry(assertionString,provenanceString,publicationInfoString, v_tuple["wasGeneratedBy"], index)
                    if ("wasDerivedFrom" in v_tuple) and (checkVirtual(v_tuple["wasDerivedFrom"])) :
                        writeVirtualEntry(assertionString,provenanceString,publicationInfoString, v_tuple["wasDerivedFrom"], index)
    except :
        print "Warning: Unable to create virtual entry."

writeVirtualRDF(virtual_list, virtual_tuples, output_file)
writeActualRDF(actual_list, actual_tuples, output_file)

if cb_fn is not None :
    try :
	cb_file = pd.read_csv(cb_fn)
    except :
        print "Error: The specified Codebook file does not exist."
        sys.exit(1)
    try :
        inner_tuple_list = []
        row_num=0
        for row in cb_file.itertuples():
            if (pd.notnull(row.Column) and row.Column not in cb_tuple) :
                inner_tuple_list=[]
            inner_tuple = {}
            inner_tuple["Code"]=row.Code
	    if(pd.notnull(row.Label)):
                inner_tuple["Label"]=row.Label
            if(pd.notnull(row.Class)) :
                inner_tuple["Class"]=row.Class
            inner_tuple_list.append(inner_tuple)
            cb_tuple[row.Column]=inner_tuple_list
            row_num += 1
    except :
        print "Warning: Unable to process Codebook file"

def convertFromCB(dataVal,column_name) :
    if column_name in cb_tuple :
        for tuple_row in cb_tuple[column_name] :
            #print tuple_row
            #if (tuple_row['Code'].__str__() is dataVal.__str__()) :
            if ("Code" in tuple_row) :
                if ("Class" in tuple_row) and (tuple_row['Class'] is not "") :
                    return tuple_row['Class']     
                else :
                    return "\"" + tuple_row['Label'] + "\"^^xsd:String"
        return "\"" + dataVal + "\""
    else :
        return "\"" + dataVal + "\""

def writeVirtualEntry(assertionString,provenanceString,publicationInfoString, v_column, index) : 
    try :
        for v_tuple in virtual_tuples :
            if (v_tuple["Column"] == v_column) :
                if "Study" in v_tuple :
                    #print "Got to Study\n"
                    continue
                else :
                    assertionString += "\n\t" + kb + v_tuple["Column"][2:] + "-" + index + "\trdf:type\t" + kb + v_tuple["Column"][2:]
                    if "Entity" in v_tuple :
                        assertionString += ";\n\t\trdf:type\t" + v_tuple["Entity"]
                    if "Attribute" in v_tuple :
                        assertionString += ";\n\t\trdf:type\t" + v_tuple["Attribute"]
                    if "Subject" in v_tuple :
                        assertionString += ";\n\t\tsio:hasIdentifier " + kb + v_tuple["Subject"] + "-" + index
                    if "inRelationTo" in v_tuple :
                        if ("Role" in v_tuple) and ("Relation" not in v_tuple) :
                            assertionString += " ;\n\t\tsio:hasRole [ rdf:type\t" + v_tuple["Role"] + " ;\n\t\t\tsio:inRelationTo " + convertVirtualToKGEntry(v_tuple["inRelationTo"], index) + " ]"
                        elif ("Role" not in v_tuple) and ("Relation" in v_tuple) :
                            assertionString += " ;\n\t\t" + v_tuple["Relation"] + " " + convertVirtualToKGEntry(v_tuple["inRelationTo"],index)
                        elif ("Role" not in v_tuple) and ("Relation" not in v_tuple) :
                            assertionString += " ;\n\t\tsio:inRelationTo " + convertVirtualToKGEntry(v_tuple["inRelationTo"],index)
                    assertionString += " .\n"
                    if "wasGeneratedBy" in v_tuple : 
                        provenanceString += " ;\n\t\tprov:wasGeneratedBy " + convertVirtualToKGEntry(v_tuple["wasGeneratedBy"],index)
                    if "wasDerivedFrom" in v_tuple : 
                        provenanceString += " ;\n\t\tprov:wasDerivedFrom " + convertVirtualToKGEntry(v_tuple["wasDerivedFrom"],index)
                    if not provenanceString is "" :
                        provenanceString += " .\n"
                    if ("wasGeneratedBy" in v_tuple ) and (checkVirtual(v_tuple["wasGeneratedBy"])) :
                        writeVirtualEntry(assertionString,provenanceString,publicationInfoString, v_tuple["wasGeneratedBy"], index)
                    if ("wasDerivedFrom" in v_tuple) and (checkVirtual(v_tuple["wasDerivedFrom"])) :
                        writeVirtualEntry(assertionString,provenanceString,publicationInfoString, v_tuple["wasDerivedFrom"], index)
    except :
        print "Warning: Unable to create virtual entry."

if data_fn is not None :
	try :
	    data_file = pd.read_csv(data_fn)
	except :
	    print "Error: The specified Data file does not exist."
	    sys.exit(1)
	try :
	    # ensure that there is a column annotated as the sio:Identifier or hasco:originalID in the data file:
	    # TODO make sure this is getting the first available ID property for the _subject_ (and not anything else)
	    id_index=None
	    row_num = 1
	    col_headers=list(data_file.columns.values)
	    try:
		for a_tuple in actual_tuples :
			#print a_tuple["Column"]
			if ((a_tuple["Attribute"] == "hasco:originalID") or (a_tuple["Attribute"] == "sio:Identifier")) :
				if(a_tuple["Column"] in col_headers) :
					print a_tuple["Column"]
					id_index = col_headers.index(a_tuple["Column"])
					for v_tuple in virtual_tuples :
						if (a_tuple["isAttributeOf"] == v_tuple["Column"]) :
							v_tuple["Subject"]=a_tuple["Column"].replace(" ","_")
			if (id_index is None) :
				print "Error: To process Data it is necessary to have a \"hasco:originalID\" or \"sio:Identifier\" Attribute in the SDD."
				sys.exit(1)
	    except: 
			print "Error processing column headers"

            for row in data_file.itertuples() :
        	        #print row
        	        if row_num==1:
        	            output_file.write(kb + "head-" + row[id_index] + " {")
        	            output_file.write("\n\t" + kb + "nanoPub-" + row[id_index])
        	            output_file.write("\n\t\trdf:type np:Nanopublication")
        	            output_file.write(" ;\n\t\tnp:hasAssertion " + kb + "assertion-" + row[id_index])
        	            output_file.write(" ;\n\t\tnp:hasProvenance " + kb + "provenance-" + row[id_index])
        	            output_file.write(" ;\n\t\tnp:hasPublicationInfo " + kb + "pubInfo-" + row[id_index])
        	            output_file.write(" .\n}\n\n")# Nanopublication head
        	        #if '\t' in row[0] :
        	        #    row = re.split(r'\t+',row[0])
        	        try :
        	    	    vref_list = []
        	    	    for a_tuple in actual_tuples :
        	    	        #print a_tuple
        	    	        if (a_tuple["Column"] in data_key ) :
        	    	            try :
        	    	                assertionString += "\n\t" + kb + a_tuple["Column"].replace(" ","_") + "-" + row[id_index] + "\trdf:type\t" + a_tuple["Attribute"]
        	    	                assertionString += " ;\n\t\trdf:type\t" + kb + a_tuple["Column"].replace(" ","_")
        	    	                assertionString += " ;\n\t\tsio:isAttributeOf " + convertVirtualToKGEntry(a_tuple["isAttributeOf"],row[id_index])
        	    	                if checkVirtual(a_tuple["isAttributeOf"]) :
        	    	                    if a_tuple["isAttributeOf"] not in vref_list :
        	    	                        vref_list.append(a_tuple["isAttributeOf"])
        	    	                if "Unit" in a_tuple :
        	    	                   assertionString += " ;\n\t\tsio:hasUnit " + a_tuple["Unit"]
        	    	                if "Time" in a_tuple :
        	    	                   assertionString += " ;\n\t\tsio:existsAt " + convertVirtualToKGEntry(a_tuple["Time"], row[id_index])
        	    	                   if checkVirtual(a_tuple["Time"]) :
        	    	                        if a_tuple["Time"] not in vref_list :
        	    	                            vref_list.append(a_tuple["Time"])
        	    	                if "Label" in a_tuple :
        	    	                    assertionString += " ;\n\t\trdfs:label \"" + a_tuple["Label"] + "\"^^xsd:String"
        	    	                if "Comment" in a_tuple :
        	    	                        assertionString += " ;\n\t\trdfs:comment \"" + a_tuple["Comment"] + "\"^^xsd:String"
        	    	                try :
        	    	                    if (row[data_key.index(a_tuple["Column"])] != "") :
        	    	                        #print row[data_key.index(a_tuple["Column"])]
        	    	                        if (cb_fn is not None) :
        	    	                            assertionString += " ;\n\t\tsio:hasValue\t" + convertFromCB(row[data_key.index(a_tuple["Column"])],a_tuple["Column"])
        	    	                        else :
        	    	                            assertionString += " ;\n\t\tsio:hasValue\t\"" + row[data_key.index(a_tuple["Column"])] + "\""
        	                    	except :
        	                        	print "Error writing data value"
        	                        assertionString += " .\n"
        	                    	provenanceString += "\n\t" + kb + a_tuple["Column"].replace(" ","_") + "-" + row[id_index] + "\tprov:generatedAtTime\t\"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime "
        	                    	if "wasDerivedFrom" in a_tuple :
        	                        	provenanceString += " ;\n\t\tprov:wasDerivedFrom\t" + convertVirtualToKGEntry(a_tuple["wasDerivedFrom"], row[id_index])
        	                        if checkVirtual(a_tuple["wasDerivedFrom"]) :
        	                            if a_tuple["wasDerivedFrom"] not in vref_list :
        	                                vref_list.append(a_tuple["wasDerivedFrom"])
        	                	if "wasGeneratedBy" in a_tuple :
        	                	        provenanceString += " ;\n\t\tprov:wasGeneratedBy\t" + convertVirtualToKGEntry(a_tuple["wasGeneratedBy"], row[id_index])
        	                        if checkVirtual(a_tuple["wasGeneratedBy"]) :
        	                        	if a_tuple["wasGeneratedBy"] not in vref_list :
        	                        	        vref_list.append(a_tuple["wasGeneratedBy"])
        	                	if "inRelationTo" in a_tuple :
        	                	        if checkVirtual(a_tuple["inRelationTo"]) :
        	                	            if a_tuple["inRelationTo"] not in vref_list :
        	                	                vref_list.append(a_tuple["inRelationTo"])
        	                        if "Relation" in a_tuple :
        	                        	provenanceString += " ;\n\t\t" + a_tuple["Relation"] + "\t" + convertVirtualToKGEntry(a_tuple["inRelationTo"], row[id_index])
        	                        else :
        	                        	provenanceString += " ;\n\t\tsio:inRelationTo\t" + convertVirtualToKGEntry(a_tuple["inRelationTo"], row[id_index])
        	                	provenanceString += " .\n"
					publicationInfoString += "\n\t" + kb + a_tuple["Column"].replace(" ","_") + "-" + row[id_index]
                			publicationInfoString += "\n\t\tprov:generatedAtTime \"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime "
        	                	if "hasPosition" in a_tuple :
        	                    		publicationInfoString += ";\n\t\thasco:hasPosition\t" + a_tuple["hasPosition"] + " .\n"
        	                    except :
        	                    	print "Unable to process tuple" + a_tuple.__str__()
        	        	    for vref in vref_list :
		        	            writeVirtualEntry(assertionString,provenanceString,publicationInfoString, vref, row[id_index])
			except:
        	        	print "Error: Something went wrong when processing actual tuples."
        	        	sys.exit(1)
        		output_file.write(kb + "assertion-" + row[id_index] + " {")
        		output_file.write(assertionString + "\n}\n\n")
        		output_file.write(kb + "provenance-" + row[id_index] + " {")
        		provenanceString = "\n\t" + kb + "assertion-" + row[id_index] + " prov:generatedAtTime \"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime .\n" + provenanceString
        		output_file.write(provenanceString + "\n}\n\n")
        		output_file.write(kb + "pubInfo-" + row[id_index] + " {")
        		publicationInfoString = "\n\t" + kb + "nanoPub-" + row[id_index] + " prov:generatedAtTime \"" + "{:4d}-{:02d}-{:02d}".format(datetime.utcnow().year,datetime.utcnow().month,datetime.utcnow().day) + "T" + "{:02d}:{:02d}:{:02d}".format(datetime.utcnow().hour,datetime.utcnow().minute,datetime.utcnow().second) + "Z\"^^xsd:dateTime .\n" + publicationInfoString
        		output_file.write(publicationInfoString + "\n}\n\n")
		    	row_num += 1
	except :
		print "Warning: Unable to process Data file"

#sdd_file.close()
output_file.close()


