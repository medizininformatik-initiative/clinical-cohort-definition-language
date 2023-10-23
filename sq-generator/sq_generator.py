import json
from datetime import datetime, timedelta
import sys, getopt
import os
import warnings

META_PROFILES_FILE = "sq-generator/meta-profiles.json"


def birthdate_to_age(birthdate_str):
    birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d')
    today = datetime.today()

    age = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        age -= 1
    return age


def extract_consent_term_codes(testcase):
    if "provision" not in testcase:
        raise KeyError(f"Could not generate term codes for resource with id {testcase['id']} because key 'provision' is missing")
    elif "provision" not in testcase["provision"]:
        raise KeyError(f"Could not generate term codes for resource with id {testcase['id']} because key 'provision.provision' is missing")
    elif len(testcase["provision"]["provision"]) == 0:
        raise Exception(f"Could not generate term codes for resource with id {testcase['id']} because length of provision.provision is 0")
    
    term_codes = []
    for provision in testcase["provision"]["provision"]:
        if "code" not in provision:
            raise KeyError(f"Missing key in provision.provision of resource with id {testcase['id']}: code")
        for code in provision["code"]:
            if "coding" not in code:
                raise KeyError(f"Missing key in a code of provision.provision of resource with id {testcase['id']}: coding")
            term_codes += (code["coding"])
    
    if len(term_codes) == 0:
        raise Exception(f"Could not generate term codes for resource with id {testcase['id']} because its povision.provision does not contain at least one code with a non-empty coding")
    return term_codes


def extract_med_administration_term_codes(testcase, testdata_id_map):
    if "medicationReference" not in testcase:
        raise KeyError(f"Could not generate term codes for resource with id {testcase['id']} because key 'medicationReference' is missing")
    elif "reference" not in testcase["medicationReference"]:
        raise KeyError(f"Could not generate term codes for resource with id {testcase['id']} because key 'reference' is missing in medicationReference")
    
    ref_id = testcase["medicationReference"]["reference"].split("/")[1]  
    if ref_id not in testdata_id_map:
        raise KeyError(f"Could not generate term codes for resource with id {testcase['id']} because referenced resource with id {ref_id} is missing in the bundle")

    ref_medication = testdata_id_map[ref_id]
    if "code" not in ref_medication:
        raise KeyError(f"Could not generate term codes for resource with id {testcase['id']} because key 'code' is missing in the referenced resource with id {ref_id}")
    elif "coding" not in ref_medication["code"]:
        raise KeyError(f"Could not generate term codes for resource with id {testcase['id']} because key 'code.coding' is missing in the referenced resource with id {ref_id}")
    elif len(ref_medication["code"]["coding"]) == 0:
        raise Exception(f"Could not generate term codes for resource with id {testcase['id']} because code.coding is empty in the referenced resource with id {ref_id}")

    return ref_medication["code"]["coding"]


def extract_term_codes_by_id_path(testcase, meta_profile):
    term_code_param = meta_profile["term_code_defining_id"].split(":")[0]
    nested_params = term_code_param.split(".")[1:]
    term_codes = testcase
    for i in range(len(nested_params)):
        param = nested_params[i]
        if param not in term_codes:
            raise KeyError(f"Could not generate term codes for resource with id {testcase['id']} key {'.'.join([str(x) for x in nested_params[0:i+1]])} is missing")
        term_codes = term_codes[param]

    if len(term_codes) == 0:
        raise Exception(f"Could not generate term codes for resource with id {testcase['id']} because length of {term_code_param} is 0")
    return term_codes


def add_missing_display_to_termcodes(term_codes):
    for term_code in term_codes:
        if not "display" in term_code:
            term_code["display"] = "someDisplay"


def extract_term_codes(testcase, meta_profile, testdata_id_map):
    term_codes = None
    resource_type = testcase["resourceType"]
    if resource_type == "Consent":
        term_codes = extract_consent_term_codes(testcase)
    elif resource_type == "MedicationAdministration":
        term_codes = extract_med_administration_term_codes(testcase, testdata_id_map)
    elif "term_code_defining_id" in meta_profile:
        term_codes = extract_term_codes_by_id_path(testcase, meta_profile)
    elif "term_codes" in meta_profile:
        term_codes =  meta_profile["term_codes"]
    else:
        raise Exception(f"Could not generate term codes because resouce with id {testcase['id']} is neither one of the edgecases Consent and MedicatinAdministration, nor does it's meta profile contain term_codes or a term_code_defining_id")

    add_missing_display_to_termcodes(term_codes)
    
    return term_codes
    


def extract_concept_value_filter(testcase, value_parameter):
    if "coding" not in testcase[value_parameter]:
        warnings.warn(f"Could not generate term codes for resouce with id {testcase['id']} because key '{value_parameter}.coding' is missing")
        return None
    elif len(testcase[value_parameter]["coding"]) == 0:
        warnings.warn(f"Could not generate term codes for resource with id {testcase['id']} because length of {value_parameter}.coding is 0")

    value_filter = {"type": "concept"}
    value_filter["selectedConcepts"] = testcase[value_parameter]["coding"]
    return value_filter


def extract_quantity_value_filter(testcase, value_parameter):
    if "code" not in testcase[value_parameter]:
        warnings.warn(f"Could not generate term codes for resouce with id {testcase['id']} because key '{value_parameter}.code' is missing")
        return None
    elif "value" not in testcase[value_parameter]:
        warnings.warn(f"Could not generate term codes for resouce with id {testcase['id']} because key '{value_parameter}.value' is missing")
        return None

    value_filter = {"type": "quantity-comparator"} 
    value_filter["unit"] = {"code": testcase[value_parameter]["code"], "display": "someDisplay"} 
    value_filter["value"] = testcase[value_parameter]["value"]
    value_filter["comparator"] = "eq" 
    return value_filter


def extract_birthdate_value_filter(testcase, value_parameter):
    value_filter = {"type": "quantity-comparator"}
    value_filter["unit"] = {"code": "a", "display": "someDisplay"} 
    value_filter["value"] = birthdate_to_age(testcase[value_parameter])
    value_filter["comparator"] = "eq"
    return value_filter


def exctract_gender_value_filter(testcase, value_parameter, meta_profile):
    value_filter = {"type":  "concept"}
    value_filter["selectedConcepts"] = [{"code": testcase[value_parameter], "system": meta_profile["concept_system"], "display": "someDisplay"}]
    return value_filter


def extract_value_filter(testcase, meta_profile):
    if "value_defining_id" not in meta_profile: 
        return None
    value_parameter = meta_profile["value_defining_id"].split(".")[1]
    if value_parameter not in testcase:
        warnings.warn(f"Could not generate value filter for resource with id {testcase['id']} because {value_parameter} is missing")
        return None
    
    
    match value_parameter:
        case "valueCodeableConcept":
            return  extract_concept_value_filter(testcase, value_parameter)
        case "valueQuantity":
            return extract_quantity_value_filter(testcase, value_parameter)
        case "birthDate":
            return extract_birthdate_value_filter(testcase, value_parameter)
        case "gender":
            return exctract_gender_value_filter(testcase, value_parameter, meta_profile)
    
def generate_reference_filter(testcase, extension, testdata_id_map, meta_profiles, specimen_code):
    if not "valueReference" in extension:
        warnings.warn(f"Could not generate referenced criterion filter for an extension of resource with id {testcase['id']} because key 'extension.valueReference' is missing")
        return None
    if not "reference" in extension["valueReference"]:
        warnings.warn(f"Could not generate referenced criterion filter for an extension of resource with id {testcase['id']} because key 'extension.valueReference.reference' is missing")
        return None
    
    reference_filter = {"type": "reference", "attributeCode": specimen_code}
    ref_id = extension["valueReference"]["reference"].split("/")[1]  

    if ref_id not in testdata_id_map:
        warnings.warn(f"Could not generate referenced criterion filter for an extension of resource with id {testcase['id']} because referenced resource with id {ref_id} is missing in the bundle")
        return None
    
    referenced_condition = testdata_id_map[ref_id]
    referenced_criteria = generate_criteria(referenced_condition, testdata_id_map, meta_profiles)
    reference_filter["criteria"] = referenced_criteria 

    return reference_filter

def generate_concept_attribute_filter(testcase, specimen_code):
    try:
        attribute_filter =  {"type": "concept", "attributeCode": specimen_code}
        attribute_filter["selectedConcepts"] = testcase["collection"]["bodySite"]["concept"]["coding"]
        return attribute_filter
    except:
        warnings.warn(f"Could not generate concept filter for resource with id {testcase['id']} because collection.bodySite.concept.coding is missing")
        return None
    

def extract_specimen_filters(testcase, testdata_id_map, meta_profiles):
    #specimen_code is currently hardcoced because i don't see a generic way to find it
    specimen_code = {"code": "Specimen.collection.bodySite", "system": "mii.module_specimen", "display": "someDisplay"}

    attribute_filters = []
    if "extension" in testcase:
        for extension in testcase["extension"]:
            if (reference_filter := generate_reference_filter(testcase, extension, testdata_id_map, meta_profiles, specimen_code)):
                attribute_filters.append(reference_filter)
    
    if (concept_filter := generate_concept_attribute_filter(testcase, specimen_code)):
        attribute_filters.append(concept_filter)
    
    return attribute_filters if attribute_filters else None


def extract_attribute_filters(testcase, testdata_id_map, meta_profiles):
    if testcase["resourceType"] == "Specimen":
        return extract_specimen_filters(testcase, testdata_id_map, meta_profiles)
    else:
        return None


def extract_time_restriction(testcase, meta_profile):
    if not "time_restriction_defining_id" in meta_profile:
        return None
    
    time_param_sequence = meta_profile["time_restriction_defining_id"].split("[")[0].split(".")[1:]
    time_param_sequence[len(time_param_sequence) -1] = time_param_sequence[len(time_param_sequence) -1] + "DateTime"
    date_time = testcase

    for  time_param in time_param_sequence:
        if not time_param in date_time:
            warnings.warn(f"Could not generate time restriction for resource with id {testcase['id']} because key {time_param} of necessary keys {time_param_sequence} is missing")
            return None
        date_time = date_time[time_param]
    
    date = datetime.strptime(date_time.split("T")[0], "%Y-%m-%d")
    return {"beforeDate": (date+timedelta(days=1)).strftime("%Y-%m-%d"), "afterDate": (date -timedelta(days=1)).strftime("%Y-%m-%d")}


def generate_criteria(testcase, testdata_id_map, meta_profiles):    
    criteria = []
    found_meta_profile = False
    for meta_profile in meta_profiles:
        criterion = {}
        
        if meta_profile["resource_type"] != testcase["resourceType"]:  
            continue
        found_meta_profile = True
        
        criterion["context"] = meta_profile["context"]
        criterion["termCodes"] = extract_term_codes(testcase, meta_profile, testdata_id_map)


        if (value_filter := extract_value_filter(testcase, meta_profile)):
            criterion["valueFilter"] = value_filter
        if (attribute_filters := extract_attribute_filters(testcase, testdata_id_map, meta_profiles)):
            criterion["attributeFilters"] = attribute_filters
        if (time_restriction := extract_time_restriction(testcase, meta_profile)):
            criterion["timeRestriction"] = time_restriction

        criteria.append(criterion)    

    if not found_meta_profile:
        raise Exception(f"Could not generate criterion for resouce with id {testcase['id']} because resource type {testcase['resourceType']} could not be handled")
    return criteria


def read_files(testdata_file):
    meta_profiles, testdata = None, None

    with open(META_PROFILES_FILE, 'r') as f:
        meta_profiles = json.load(f)
    with open(testdata_file, 'r') as f:
        testdata = json.load(f).get("entry")

    return meta_profiles, testdata


def read_args():
    testdata_file, output_dir = None, "./"
    opts, _ = getopt.getopt(sys.argv[1:], 'i:o:')

    for opt, arg in opts:
        if opt in ('-i', '--input-file'):
            testdata_file = arg
        elif opt in ('-o', '--output-dir'):
            output_dir = arg
        elif opt in ('-h', '--help'):
            print("Usage: sq-generator.py -i <input-json> -o <output-dir>")
    
    return testdata_file, output_dir


def init_testdata_id_map(testdata):
    testdata_id_map = {}
    for data in testdata:
        id = data["resource"]["id"]
        testdata_id_map[id] = data["resource"]

    return testdata_id_map

def build_sq_from_inclusin_criteria(criteria):
    sq = {"version": "https://medizininformatik-initiative.de/fdpg/StructuredQuery/v3/schema"}
    sq["inclusionCriteria"] = [criteria]
    return sq


def main():
    testdata_file, output_dir = read_args()
    meta_profiles, testdata = read_files(testdata_file)
    testdata_id_map = init_testdata_id_map(testdata)

    for file_count, data in enumerate(testdata):
        if data["resource"]["resourceType"] == "Medication":
            continue
        criteria = generate_criteria(data["resource"], testdata_id_map, meta_profiles)
        if len(criteria) == 0:
            raise Exception(f"Could not generate criteria from resource with id {data['resource']['id']}")

        sq = build_sq_from_inclusin_criteria(criteria)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(f"{output_dir}sq-{file_count}.json", "w") as f:
            f.write(json.dumps(sq, indent=4))
            f.write("\n")


if __name__ == "__main__":
    main()
