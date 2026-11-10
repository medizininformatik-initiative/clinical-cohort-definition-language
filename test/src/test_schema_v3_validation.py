import copy
import glob
import json

import jsonschema
import pytest

SCHEMA_FILE = "json-schema/clinical-cohort-definition-language-schema-v3-draft.json"
V3_EXAMPLES = sorted(glob.glob("ccdl-tests/ccdl-v3/*.json"))

TERM_CODE = {"code": "somecode-4591", "system": "somesystem-1138", "display": "somedisplay-5832"}
CONTEXT = {"code": "somecode-4465", "system": "somesystem-2561", "display": "somedisplay-0684"}


@pytest.fixture
def schema():
    with open(SCHEMA_FILE, 'r') as file:
        return json.load(file)


def criterion():
    return {"termCodes": [copy.deepcopy(TERM_CODE)], "context": copy.deepcopy(CONTEXT)}


def anchor_and_dependent():
    """An anchor group and a group windowed relative to it, in one group array."""
    return {
        "version": "3",
        "inclusionCriteria": [[
            {"id": "anchor", "anchorOccurrence": "first", "criteria": [[criterion()]]},
            {"id": "dependent",
             "relativeTimeRestrictions": [{"anchorRef": "anchor", "minOffset": "-P3D", "maxOffset": "PT72H"}],
             "criteria": [[criterion()]]},
        ]],
    }


def assert_rejected(ccdl, schema):
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(ccdl, schema)


def test_examples_found():
    assert len(V3_EXAMPLES) >= 10


@pytest.mark.parametrize("example_file", V3_EXAMPLES)
def test_v3_example_validates(example_file, schema):
    with open(example_file, 'r') as file:
        jsonschema.validate(json.load(file), schema)


def test_anchor_and_dependent(schema):
    jsonschema.validate(anchor_and_dependent(), schema)


def test_anchor_with_or_clause_accepted(schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][0]["criteria"] = [[criterion(), criterion()]]
    jsonschema.validate(ccdl, schema)


def test_multi_clause_anchor_rejected(schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][0]["criteria"] = [[criterion()], [criterion()]]
    assert_rejected(ccdl, schema)


def test_multi_clause_dependent_accepted(schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][1]["criteria"] = [[criterion()], [criterion()]]
    jsonschema.validate(ccdl, schema)


def test_exclusion_side_accepted(schema):
    ccdl = anchor_and_dependent()
    ccdl["exclusionCriteria"] = [[{"relativeTimeRestrictions": [{"anchorRef": "anchor", "maxOffset": "P2D"}],
                                   "criteria": [[criterion(), criterion()]]}]]
    jsonschema.validate(ccdl, schema)


def test_now_criterion_accepted(schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][0] = {"id": "anchor", "criteria": [[{"type": "now"}]]}
    jsonschema.validate(ccdl, schema)


def test_now_criterion_with_term_codes_rejected(schema):
    ccdl = anchor_and_dependent()
    now = {"type": "now", "termCodes": [copy.deepcopy(TERM_CODE)]}
    ccdl["inclusionCriteria"][0][0] = {"id": "anchor", "criteria": [[now]]}
    assert_rejected(ccdl, schema)


def test_wrong_version_rejected(schema):
    ccdl = anchor_and_dependent()
    ccdl["version"] = "2"
    assert_rejected(ccdl, schema)


def test_v2_shape_rejected(schema):
    ccdl = {"version": "3", "inclusionCriteria": [[criterion()]]}
    assert_rejected(ccdl, schema)


def test_flat_group_array_rejected(schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"] = ccdl["inclusionCriteria"][0]
    assert_rejected(ccdl, schema)


def test_flat_criteria_rejected(schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][1]["criteria"] = [criterion()]
    assert_rejected(ccdl, schema)


def test_group_without_criteria_rejected(schema):
    ccdl = anchor_and_dependent()
    del ccdl["inclusionCriteria"][0][1]["criteria"]
    assert_rejected(ccdl, schema)


def test_empty_relative_time_restrictions_rejected(schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][1]["relativeTimeRestrictions"] = []
    assert_rejected(ccdl, schema)


def test_restriction_without_bounds_rejected(schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][1]["relativeTimeRestrictions"] = [{"anchorRef": "anchor"}]
    assert_rejected(ccdl, schema)


def test_single_restriction_object_rejected(schema):
    ccdl = anchor_and_dependent()
    group = ccdl["inclusionCriteria"][0][1]
    group["relativeTimeRestrictions"] = group["relativeTimeRestrictions"][0]
    assert_rejected(ccdl, schema)


def test_unknown_anchor_occurrence_rejected(schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][0]["anchorOccurrence"] = "latest"
    assert_rejected(ccdl, schema)


@pytest.mark.parametrize("offset", ["P0D", "-P3D", "+P1D", "PT72H", "-PT24H", "P1DT12H", "PT30M", "PT0.5S"])
def test_duration_accepted(offset, schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][1]["relativeTimeRestrictions"][0]["minOffset"] = offset
    jsonschema.validate(ccdl, schema)


@pytest.mark.parametrize("offset", ["P", "PT", "P1DT", "P1M", "P1Y", "P1W", "P-1D", "3D", "-PT", "P1H"])
def test_duration_rejected(offset, schema):
    ccdl = anchor_and_dependent()
    ccdl["inclusionCriteria"][0][1]["relativeTimeRestrictions"][0]["minOffset"] = offset
    assert_rejected(ccdl, schema)
