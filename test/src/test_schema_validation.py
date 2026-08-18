import jsonschema
import json
import copy
import pytest

SCHEMA_FILE = "json-schema/clinical-cohort-definition-language-schema.json"
EXAMPLE_JSON_FILE = "example-json/ccdl-all-properties.json"

TERM_CODE = {"code": "somecode-4591", "system": "somesystem-1138", "display": "somedisplay-5832"}
CONTEXT = {"code": "somecode-4465", "system": "somesystem-2561", "display": "somedisplay-0684"}
UNIT = {"code": "somecode-8331", "display": "somedisplay-1269"}
ATTRIBUTE_CODE = {"code": "somecode-0103", "system": "somesystem-3571", "display": "somedisplay-9567"}


@pytest.fixture
def schema():
    loaded_schema = None
    with open(SCHEMA_FILE, 'r') as file:
        loaded_schema = json.load(file)
    return loaded_schema


def basic_ccdl():
    ccdl = {}
    ccdl["inclusionCriteria"] = [[{"termCodes": [copy.deepcopy(TERM_CODE)], "context": CONTEXT}]]
    ccdl["version"] = "2"
    return ccdl


def test_basic_ccdl(schema):
    jsonschema.validate(basic_ccdl(), schema)


def test_example_json(schema):
    example_json = None
    with open(EXAMPLE_JSON_FILE, 'r') as file:
        example_json = json.load(file)

    jsonschema.validate(example_json, schema)


def test_wrong_version_rejected(schema):
    ccdl = basic_ccdl()

    ccdl["version"] = "2.0.0"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(ccdl, schema)
