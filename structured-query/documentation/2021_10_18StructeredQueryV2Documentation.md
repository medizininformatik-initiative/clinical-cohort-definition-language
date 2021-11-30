
# Structured Queries

CODEX front-end allows users to create  feasibility queries based on inclusion and exclusion criteria. The different inclusion and exclusion criteria are conjuncted with the "AND" and "OR" operators respectively. Resulting in a conjunctive normal form without negation (CNF) for inclusion and disjunctive normal form without negation (DNF) for the exclusion  criteria.

The front-end created queries need to be transmitted to different back-end services which translates the Structured Query format into other query formats such as FHIR Search or CQL. As common data exchange format the so called *Structured Queries* are defined.

## Query Message

At its core each *Structured Query* has a metadata header and the query body holding the structured query.

### Query Metadata

The metadata provides some basic information about the query:

| Name      | Description                            |
| :-------- | -------------------------------------- |
| Version   | API Version                            |
| Timestamp | Timestamp when the query was sent      |
| queryId   | unique Id to identify a specific query |

## Query

As previously introduced, the query is based on inclusion and exclusion criteria represented in CNF and DNF. 

With in the query, both CNF and DNF are conjunct with an "AND NOT" operator. 

For the normal form, different building blocks are provided to represent the conjunctions of criteria.

## inclusionCriteria\[][]

Given a CNF:  A and (B or C)

The inclusionCriteria is an array of arrays of criteria. Within the outer array, all elements are conjunct with "AND". Based on the example {A} {B or C}.

Within the inner array all elements are disjunct with "OR". Based on the example {B}{C}. A special case is given if only one element is given, e.g. {A}. In this case, no logic operation is applied to this element in this hierarchic element.

-> inclusionCriteria= {{A}, {B, C}}

## exclusionCriteria\[][]

Analog for the exclusion criteria:

Given a DNF:  A or (B and C)

The exclusionCriteria is an array of arrays of criteria. Within the outer array, all elements are disjunct with "OR". Based on the example {A} {B and C}.

Within the inner array all elements are conjunct with "And". Based on the example {B}{C} . A special case is given if only one element is given, e.g. {A}. In this case, no logic operation is applied to this element in this hierarchic element.

-> exclusionCriteria = {{A},  {B, C}}

## criterion

The previous introduced elements {A}, {B} and {C} are representative for different criteria. 

Each criterion represents a unique concept or statement, which is identified by its termCodes. A criterion can have multiple TermCodes if they are synonymous and mapped identically.  Which can be further specified by applying a value filter.

## termCode

The termCode defines a concept based on a coding system (i.e. LOINC). The triplet of code, system and version identify the concept. An additional display element allows for a human-readable form (This value SHALL be the same as the value define by the coding system)

## valueFilter

ValueFilter specify the value of a defined concept. Depending on the valueFilter Type, different value statements can be made. The valueFilter restricts the value of the highest interest of the resource.

### quantity-comperator

A valueFilter of type quantity-comperator can be applied to all numeric criterion concepts. It allows to use the common comparators represented as enumeration values:

| Enumeration | Comparator |
| ----------- | ---------- |
| gt          | >          |
| lt          | <          |
| ge          | ≥          |
| le          | ≤          |
| eq          | =          |
| ne          | !=         |

 The concept value is compared with the given value. A unit can be used in the comparison.

### quantity-range

A valueFilter of type quantity-range can be applied to all numeric criterion concepts to validate if a value is within the boundaries of the defined min and max values. Again a unit can be given.

### DateTime-comperator

A valueFilter of type datetype can be applied to all datetime criterion concepts. It allows to use the 

| Enumeration | Comparator    |
| ----------- | ------------- |
| le          | less equal    |
| ge          | greater equal |

ISO Datum 

### DateTime-range

A valueFilter of type datetime-range can be applied to all datetime criterion concepts to validate if a value is an overlap exists between the criterions datetime and the interval explicitly or implicitly defined by the before and/or afterDate. ISO dateformat.

beforeDate

afterDate  

### Concept-ValueFilter

A valueFilter of type concept can be applied to all concepts which have a value which itself is defined by a concept. The Value can be restricted by selectedConcepts which are termCodes. If multiple selectedConceptsare given the criterion is fulfilled if one of the values matches. 

Example:

The patient gender is a concept and can be represented with a Termcode. The values female, male, diverse, etc. are also concepts representable by termCodes.

"All male or female patients " (PseudoCriterion): 

```json
{
  "inclusionCriteria": [
    [
      {
        "termCode": [ {
          "code": "LL2191-6",
          "display": "Geschlecht",
          "system": "http://loinc.org"
        } ],
        "valueFilter": {
          "type": "concept",
          "selectedConcepts": [
            {
              "code": "F",
              "display": "female",
              "system": "https://fhir.loinc.org/CodeSystem/$lookup?system=http://loinc.org&code=LL2191-6",
              "version": ""
            },
            {
              "code": "M",
              "display": "male",
              "system": "https://fhir.loinc.org/CodeSystem/$lookup?system=http://loinc.org&code=LL2191-6",
              "version": ""
            }
          ]
        }
      }
    ]
  ]
}
```



## AttributeFilter[]

Attribute Filter are valueFilter for specific attributes of the Resource. The AttributeCode defined as termCode specifies which attribute is restricted.
