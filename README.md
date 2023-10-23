# MII feasibility Structured Query

## Includes 
* an example of a structured query (as JSON file)
* a JSON schema describing a structured query
* [documenation as .md-file](documentation/2021_10_18StructeredQueryV2Documentation.md) 
* a python script that generates structured queries that fit to custom test data

## Usage of Structured Query Generator
* the necessary test data is a FHIR bundle that should be placed in a json file like [here](test/resources/test-data.json) and is specified with the -i option
* the resulting structured queries will be saved to the current working direcotry by default, but you can specify the output directory with the -o option
#### Run
```sh 
python sq-generator/sq_generator.py -i <your-test-data.json> -o <your-output-dir/>
```
