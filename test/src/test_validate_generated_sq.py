import pytest
import os
import json
import jsonschema

SCHEMA_FILE = "json-schema/clinical-cohort-definition-language-schema.json"
GENERATED_CCDLS_DIR = "target/resources/generated-ccdls/"


@pytest.fixture
def schema():
    loaded_schema = None
    with open(SCHEMA_FILE, 'r') as file:
        loaded_schema = json.load(file)
    return loaded_schema


def read_ccdls():
    if not os.path.exists(GENERATED_CCDLS_DIR):
        return []
    ccdls = []
    for file in os.listdir(GENERATED_CCDLS_DIR):
        filename = os.fsdecode(file)
        if not filename.endswith(".json"):
            continue

        with open(f"{GENERATED_CCDLS_DIR}{filename}", 'r') as f:
            ccdls.append(json.load(f))

    return ccdls


@pytest.mark.parametrize("ccdl", read_ccdls())
def test_validate_ccdls(ccdl, schema):
    jsonschema.validate(ccdl, schema)
