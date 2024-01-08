import jsonschema
import json
import copy
import pytest

SCHEMA_FILE = "json-schema/structured-query-schema.json"
EXAMPLE_JSON_FILE = "example-json/sq-all-properties.json"

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


def basic_sq():
    sq = {}
    sq["inclusionCriteria"] = [[{"termCodes": [copy.deepcopy(TERM_CODE)], "context": CONTEXT}]]
    sq["version"] = "someVersion"
    return sq


def test_basic_sq(schema):
    jsonschema.validate(basic_sq(), schema)


def test_example_json(schema):
    example_json = None
    with open(EXAMPLE_JSON_FILE, 'r') as file:
        example_json = json.load(file)

    jsonschema.validate(example_json, schema)


def test_additional_prop_in_criterion(schema):
    sq = basic_sq()

    sq["inclusionCriteria"][0][0]["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_outermost_layer(schema):
    sq = basic_sq()

    sq["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_termcode(schema):
    sq = basic_sq()

    sq["inclusionCriteria"][0][0]["termCodes"][0]["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_time_restriction(schema):
    sq = basic_sq()
    time_restriction = {"beforeDate": "1990-01-01"}
    sq["inclusionCriteria"][0][0]["timeRestriction"] = time_restriction
    jsonschema.validate(sq, schema)

    time_restriction["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_unit(schema):
    attr_filter = {"attributeCode": ATTRIBUTE_CODE, "unit": copy.deepcopy(UNIT)}
    sq = basic_sq()
    attr_filter["comparator"] = "gt"
    attr_filter["value"] = 10
    attr_filter["type"] = "quantity-comparator"
    sq["inclusionCriteria"][0][0]["attributeFilters"] = [attr_filter]
    jsonschema.validate(sq, schema)

    attr_filter["unit"]["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_attribute_comparator_filter(schema):
    attr_filter = {"attributeCode": ATTRIBUTE_CODE, "unit": UNIT}
    sq = basic_sq()
    attr_filter["comparator"] = "gt"
    attr_filter["value"] = 10
    attr_filter["type"] = "quantity-comparator"
    sq["inclusionCriteria"][0][0]["attributeFilters"] = [attr_filter]
    jsonschema.validate(sq, schema)

    attr_filter["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_value_comparator_filter(schema):
    val_filter = {"unit": UNIT}
    sq = basic_sq()
    val_filter["comparator"] = "gt"
    val_filter["value"] = 10
    val_filter["type"] = "quantity-comparator"
    sq["inclusionCriteria"][0][0]["valueFilter"] = val_filter
    jsonschema.validate(sq, schema)

    val_filter["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_attribute_range_filter(schema):
    attr_filter = {"attributeCode": ATTRIBUTE_CODE, "unit": UNIT}
    sq = basic_sq()
    attr_filter["minValue"] = 10
    attr_filter["maxValue"] = 20
    attr_filter["type"] = "quantity-range"
    sq["inclusionCriteria"][0][0]["attributeFilters"] = [attr_filter]
    jsonschema.validate(sq, schema)

    attr_filter["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_value_range_filter(schema):
    val_filter = {"unit": UNIT}
    sq = basic_sq()
    val_filter["minValue"] = 10
    val_filter["maxValue"] = 20
    val_filter["type"] = "quantity-range"
    sq["inclusionCriteria"][0][0]["valueFilter"] = val_filter
    jsonschema.validate(sq, schema)

    val_filter["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_attribute_concept_filter(schema):
    attr_filter = {"attributeCode": ATTRIBUTE_CODE}
    sq = basic_sq()
    attr_filter["type"] = "concept"
    attr_filter["selectedConcepts"] = [TERM_CODE]
    sq["inclusionCriteria"][0][0]["attributeFilters"] = [attr_filter]
    jsonschema.validate(sq, schema)

    attr_filter["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_value_concept_filter(schema):
    val_filter = {}
    sq = basic_sq()
    val_filter["type"] = "concept"
    val_filter["selectedConcepts"] = [TERM_CODE]
    sq["inclusionCriteria"][0][0]["valueFilter"] = val_filter
    jsonschema.validate(sq, schema)

    val_filter["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_attribute_reference_filter(schema):
    attr_filter = {"attributeCode": ATTRIBUTE_CODE}
    sq = basic_sq()
    attr_filter["type"] = "reference"
    attr_filter["criteria"] = [{"termCodes": [TERM_CODE], "context": CONTEXT}]
    sq["inclusionCriteria"][0][0]["attributeFilters"] = [attr_filter]
    jsonschema.validate(sq, schema)

    attr_filter["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)


def test_additional_prop_in_referenced_criterion(schema):
    attr_filter = {"attributeCode": ATTRIBUTE_CODE}
    sq = basic_sq()
    attr_filter["type"] = "reference"
    attr_filter["criteria"] = [{"termCodes": [TERM_CODE], "context": CONTEXT}]
    sq["inclusionCriteria"][0][0]["attributeFilters"] = [attr_filter]
    jsonschema.validate(sq, schema)

    attr_filter["criteria"][0]["foo"] = "bar"
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(sq, schema)
