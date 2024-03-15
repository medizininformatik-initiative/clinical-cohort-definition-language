
# Clinical Cohort Definition Language


The Clinical Cohort Definition Language (CCDL) was created to provide a formal definition for feasibility queries based on inclusion and exclusion criteria. The different inclusion and exclusion criteria are conjuncted with the "AND" and "OR" operators respectively. Resulting in a conjunctive normal form without negation (CNF) for inclusion and disjunctive normal form without negation (DNF) for the exclusion  criteria.

The format was chosen to be easily created from a javascript front-end as well as support simple translation to FHIR Search and CQL.


## CCDL Definition

The CCDL is based on inclusion and exclusion criteria represented in CNF and DNF. 
In the CCDL, both CNF and DNF are implicitedly joint with an "AND NOT" operator.

In addition to the inclusion and exclusion criteria, at its core each CCDL has a the following fields, that provide some basic information about the CCDL:

| Name      | Description                            |
| :-------- | -------------------------------------- |
| version   | API Version of the CCDL                |
| display   | Custom name of the CCDL                |

## Inclusion Criteria\[][]

Given a CNF:  A AND (B OR C)

The *inclusionCriteria* field holds an array of arrays of criteria. Within the outer array, all elements are conjunct with "AND". Based on the example {A} {B or C}.
Within the inner array all elements are disjunct with "OR". Based on the example {B}{C}. A special case is given if only one element is given, e.g. {A}. In this case, no logic operation is applied to this element in this hierarchic element.
-> inclusionCriteria:  [[{A}], [{B}, {C}]]  = A and (B or C)


## Exclusion Criteria\[][]

Given a DNF:  A or (B and C)

Analogous to inclusion criteria, the *exclusionCriteria* field holds an array of arrays of criteria. Within the outer array, all elements are disjunct with "OR". Based on the example {A} {B and C}.

Within the inner array all elements are conjunct with "AND". Based on the example {B}{C} . A special case is given if only one element is given, e.g. {A}. In this case, no logic operation is applied to this element in this hierarchic element.

-> exclusionCriteria = [[{A}], [{B}, {C}]]  = A OR (B AND C)

## Criterion

The previous introduced elements {A}, {B} and {C} are representative for different criteria.
Each criterion represents a unique medical concept, which is identified by its *termCodes*. A criterion can have multiple term codes if they are synonymous and mapped identically. Which can be further specified by applying a value filter.

## Term Code

A term code uniquely identifies a concept based on a coding system (i.e. LOINC) that consists of a triplet of *code*, *system* and *version*
An additional *display* field allows for a human-readable form (This value SHALL be the same as the value defined by the coding system), which is not interpreted for translation.

## Context

There are cases where the term code does not uniquely identify a criterion within an ontology as the same term code is used to describe different criteria based on a context.
For these cases the *context* introduced an additional triplet of *code*, *system* and *version*. 
The criterion is then uniquely identified by the combination of context and term code. Like a term code, context also has a *display* field.

## Value Filter

The *valueFilter* allows the filtering of the criterion by its main value (the value, which can always be expected to be set in the source system). There can only be exactly one value filter for each criterion.

Three types of the value filter exist: "quantity-comparator", "quantity-range" and "concept".

### Quantity Comparator

The type *"quantity-comparator"* can be applied to all numeric criteria. It allows the use of the folowing common comparators:

| Enumeration | Comparator |
| ----------- | ---------- |
| gt          | >          |
| lt          | <          |
| ge          | ≥          |
| le          | ≤          |
| eq          | =          |
| ne          | !=         |

 The concept value is compared with the given value. 
 A unit can be used in the comparison.

### Quantity Range

The type *"quantity-range"* can be applied to all numeric criterion concepts to validate if a value is within the boundaries of the defined *minValue* and *maxValue*.
A *unit* can be used for the comparison.


### Concept

The type *"concept"* can be applied to all criteria which have a value defined by a concept. The value can be restricted by the *selectedConcepts*, where each restricting value is represented a term code.
Multiple selected concepts are joint using "OR". 

=> If multiple concepts are selected, the criterion is fulfilled if one or more of the values matches. 


## Attribute Filters[]

Attribute filters are like value filters, but for specific attributes of the resource, and can be set independently of the value filter. 
The *attributeCode*, defined like a term code, specifies which attribute of a resource is restricted.
Attribute filters have all types of the value filter and one additional type "reference".
All attribute filters in the *attributeFilters* array are joint using "AND".

### Reference

The attribute filter of type "reference" allows one to filter a criterion by another criterion directly linked to it.
If the attribute filter is of type "reference" it contains an additional *criteria* array.
This array contains criteria the referencing criterion is linked to. 
The referenced criterion can contain any filter (*valueFilter*, *attributeFilters*, *timeRestriction*) except the attribute filter of type "reference".

Example for referenced criterion:

A biospecimen (referencing criterion) of a specific type (term code) and taken from a specific body site (attribute filter of type "concept") can be retrieved
for a specific diagnosis (refrenced criterion - diagnosis).

## Time Restriction

For each criterion a main *timeRestriction* can be applied. This time restriction specifies the interval within the critiera has to be fullfilled.
The time restriction is specified by a *afterDate* (the start of the date interval) and *beforeDate* (the end of the date interval).
If either *afterDate* or *beforeDate* is not set, the interval is open end towards the "not set" data restriction.


## Schema and Example:

Schema:  [Schema](../json-schema/clinical-cohort-definition-language-schema.json)
Example: [Example](../example-json/ccdl-all-properties.json)

