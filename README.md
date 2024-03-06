# MII feasibility Clinical Cohort Definition Language

## Includes 
* an example of a CCDL (as JSON file)
* a JSON schema describing the CCDL
* [documenation as .md-file](documentation/Documentation.md) 
* a python script that generates CCDLs that fit to custom test data

## Usage of CCDL Generator
* the necessary test data is a FHIR bundle that should be placed in a json file like [here](test/resources/test-data.json) and is specified with the -i option
* the resulting CCDLs will be saved to the current working direcotry by default, but you can specify the output directory with the -o option
#### Run
```sh 
python ccdl-generator/ccdl_generator.py -i <your-test-data.json> -o <your-output-dir/>
```
