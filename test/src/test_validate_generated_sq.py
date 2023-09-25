import pytest
import os
import json
import jsonschema

SCHEMA_FILE = "json-schema/StructuredQuery-schema-v3.json"
GENERATED_SQS_DIR = "target/resources/generated-sqs/"

@pytest.fixture
def schema():
    loaded_schema = None
    with open(SCHEMA_FILE, 'r') as file:
        loaded_schema = json.load(file)
    return loaded_schema

def read_sqs():
    if not os.path.exists(GENERATED_SQS_DIR):
        return []
    sqs = []
    for file in os.listdir(GENERATED_SQS_DIR):
        filename = os.fsdecode(file)
        if not filename.endswith(".json") : 
            continue
        
        with open(f"{GENERATED_SQS_DIR}{filename}", 'r') as f:
            sqs.append(json.load(f))

    return sqs

@pytest.mark.parametrize("sq", read_sqs())
def test_validate_sqs(sq, schema):   
    jsonschema.validate(sq, schema)
