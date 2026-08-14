# CCDL Generator

The CCDL generator is a Python script that generates CCDLs that fit custom test data.

## Usage

* the necessary test data is a FHIR bundle that should be placed in a json file like [test-data.json](https://github.com/medizininformatik-initiative/clinical-cohort-definition-language/blob/main/test/resources/test-data.json) and is specified with the `-i` option
* the resulting CCDLs will be saved to the current working directory by default, but you can specify the output directory with the `-o` option

### Run

```sh
python ccdl-generator/ccdl_generator.py -i <your-test-data.json> -o <your-output-dir/>
```
