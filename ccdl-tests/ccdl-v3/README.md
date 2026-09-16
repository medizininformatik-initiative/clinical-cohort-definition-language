# CCDL v3 worked examples

Ten `version: "3"` cohort definitions, each chosen to demonstrate a different part of the relative
time constraint extension. The specification itself is [../../ccdl-v3-draft.md](../../ccdl-v3-draft.md),
with a rules-only summary in [../../ccdl-v3-draft-tldr.md](../../ccdl-v3-draft-tldr.md). This file is
a guide to the examples, not a second copy of the spec.

## Read them in this order

| # | File | Demonstrates | Translates |
|---|---|---|---|
| 1 | `ccdl-example-hemoglobin-last-24h.json` | the minimal anchored query | yes, 18 lines CQL |
| 2 | `ccdl-example-hemoglobin-24h-after-procedure.json` | the minimal anchor on a clinical event | yes, 26 lines |
| 3 | `ccdl-with-new-time-constraint-draft.json` | the feature set in one realistic cohort | yes, 125 lines |
| 4 | `ccdl-example-or-scoped-anchors-draft.json` | the OR level and asymmetric requiredness | yes, 62 lines |
| 5 | `ccdl-example-multi-clause-anchor.json` | multi-clause AND-anchors | yes, 61 lines |
| 6 | `ccdl-example-hemoglobin-between-two-anchors.json` | two anchors on one group, windows intersected | yes, 41 lines |
| 7 | `ccdl-example-any-chained-anchors-draft.json` | `anchorOccurrence: "any"`, one anchor with two referencers | yes, 61 lines |
| 8 | `ccdl-example-any-chain-three-hops-draft.json` | `"any"` anchors stacked three deep | yes, 56 lines |
| 9 | `ccdl-example-any-multi-clause-anchor-draft.json` | a multi-clause `"any"` anchor: the witness is a tuple | yes, 34 lines |
| 10 | `ccdl-example-all-features-draft.json` | everything at once, as a reference | yes, 177 lines |

---

### 1. `ccdl-example-hemoglobin-last-24h.json` — start here

One group array, two groups, one restriction. A hemoglobin measurement in the 24 hours up to now.

- `anchor-now` — the `{"type": "now"}` criterion, an anchor that is not a clinical event. It needs no
  `anchorOccurrence`, because "now" has exactly one occurrence by definition.
- `group-hemoglobin-last-24h` — `minOffset: "-PT24H"`, `maxOffset: "PT0H"` against that anchor.

Nothing else is in play: no OR level, no fan-out, no multi-clause anchor. Read this one to see the
shape of a `relativeTimeRestrictions` entry, then move on.

### 2. `ccdl-example-hemoglobin-24h-after-procedure.json` — the same, anchored to an event

Example 1 anchors to the clock. This one is the same minimal shape anchored to something that happens
to a patient, which is what an anchor is normally for. A haemoglobin in the 24 hours after the first
laparoscopic appendectomy.

- `anchor-procedure` — one OPS code, one clause, `anchorOccurrence: "first"`.
- `group-hemoglobin-after-procedure` — `minOffset: "PT0H"`, `maxOffset: "PT24H"`.

Because the anchor is a real retrieve rather than `now`, its `"AnchorDate_anchor-procedure" is not
null` guard can actually fail, and for a patient with no appendectomy it does. That guard is the whole
of §7 in one line: a dependent whose anchor does not resolve must select nobody, and cannot be left to
the target engine's own null handling.

Two details in the output are worth seeing here rather than in a bigger file. The anchor expands to
four OPS codes, not one, because the concept tree resolves children of `5-470.1`. And `PT24H` reaches
the **following date**, not 24 clock hours: offsets are applied at the anchor date's own precision, so
a haemoglobin the next morning is inside the window and one the previous evening is not.

### 3. `ccdl-with-new-time-constraint-draft.json` — the realistic one

The broadest example. One inclusion group array, one exclusion group array, nine groups. Female
patients whose first dementia diagnosis (F00 or G30) is the index event, plus:

- `group-infection-signs-before-diagnosis` — `(CRP OR leukocytes) AND heart rate`, all inside the
  3 days up to the diagnosis. Levels 3 and 4 both in use inside one time-restricted group.
- `group-donepezil-after-diagnosis` — a medication within 30 days after the index event.
- `group-weight-since-diagnosis-window` — **an open-ended window**: `minOffset` only, no `maxOffset`.
- `anchor-now` / `group-respiratory-rate-since-now` — a second, independent anchor in the same query.
- `group-excl-anticoagulant-after-diagnosis` — an **exclusion** group anchored to an **inclusion**
  group's anchor. Anchor resolution is global and crosses sides.
- `group-excl-organ-failure` — an OR of two unanchored exclusion reasons, kept inside one group
  rather than split across group arrays.

### 4. `ccdl-example-or-scoped-anchors-draft.json` — the OR level

Three group arrays, OR'd, which is the structure §1–§3 of the spec argues for.

- Group array 1 — `group-gender` AND `group-crp-standalone`. Plain AND, no anchor.
- Group array 2 — `anchor-dementia-diagnosis` AND `group-donepezil-after-diagnosis`. The anchor is a
  required member of this path.
- Group array 3 — `group-weight-since-diagnosis-window` alone, referencing group array 2's anchor by
  id **without listing it**. It takes the anchor's date, not its truth.

Group arrays 2 and 3 are the asymmetric requiredness pattern: the same anchor is required in one path
and merely a date source in another. Note that this distinction is invisible in the generated CQL for
a single-clause anchor, because the null-guard `"AnchorDate_X" is not null` is already equivalent to
"the anchor matched". Example 5 is where the two cases produce different output.

### 5. `ccdl-example-multi-clause-anchor.json` — multi-clause anchors

`anchor-procedure` is a **two-clause AND**: two OPS codes that must both be present. A multi-clause
anchor does not collapse to one date. It keeps two, the earliest and the latest across its clauses,
and they feed the dependent's bounds asymmetrically — `maxOffset` from the earliest, `minOffset` from
the latest. The generated CQL shows this as an indexed guard, `"AnchorDate_anchor-procedure"[0]` and
`[1]`, one check per clause rather than one aggregate check.

Two group arrays share that anchor, one listing it and one only referencing it, so this is the
asymmetric pattern from example 4 again, this time where it actually changes the output.

Group array 1 also carries `group-gender`, an ordinary unanchored group AND'd in beside the anchor
and its dependent. Anchored and unanchored groups mix freely inside a group array. Keep such a filter
*inside* a group array rather than giving it one of its own: the level above the group array is OR,
so a lone demographic group would become an alternative qualifying path on its own and swallow the
rest of the query.

### 6. `ccdl-example-hemoglobin-between-two-anchors.json` — "between event A and event B"

The only example where one group carries **more than one** `relativeTimeRestrictions` entry. A
haemoglobin measured somewhere between the diverticular disease diagnosis and the resection, which is the
pre-operative anaemia window.

- `anchor-colon-diverticular-disease` — K57.3, `"first"`.
- `anchor-colon-resection` — 5-455.3, `"first"`.
- `group-hemoglobin-between-diagnosis-and-resection` — two entries, each naming a different anchor
  and each bounded on **one side only**: `minOffset: "P0D"` against the diagnosis, `maxOffset: "P0D"`
  against the resection. Every entry needs at least one offset, never both, and leaving the other
  side off is how you say "open in that direction".

The entries' windows **intersect**: `windowStart` is the `Max` of every entry's start and `windowEnd`
the `Min` of every entry's end, so one open-ended entry contributes nothing on its open side. The
generated CQL makes this literal:

```
Interval[ Max({ "AnchorDate_anchor-colon-diverticular-disease" + 0 hours, @0001-01-01T }),
          Min({ @9999-12-31T, "AnchorDate_anchor-colon-resection" + 0 hours }) ]
```

The reason this is not the same as writing two separate groups: two groups, each with one entry,
would be satisfied by **two different** haemoglobin values, one after the diagnosis and another
before the surgery. One group with two entries requires a **single** value inside both windows at
once. Reach for multiple entries only when that "one value, between A and B" reading is what you
mean. Note also that the null-guard covers every entry, so a patient missing either anchor does not
match.

### 7. `ccdl-example-any-chained-anchors-draft.json` — `any` and chaining

The only example of `anchorOccurrence: "any"`, and the only one where a group is both a dependent and
an anchor. A two-hop chain:

```
anchor-dementia-diagnosis  ("first")
  └── group-delirium-after-diagnosis   F05, P0D..P30D after the diagnosis, "any"
        ├── group-haloperidol-after-delirium   N05AD01, P0D..P3D after the episode
        └── group-sodium-around-delirium       2951-2,  -P1D..P1D around the episode
```

Two things to take from it.

**The chain.** `group-delirium-after-diagnosis` carries its own window and is also an anchor, so the
candidate set its two dependents resolve against is its already-window-filtered matches. A delirium
outside the 30-day window cannot date anything downstream.

**The shared witness.** Both dependents name the same anchor inside one group array, so they are bound
to the *same* delirium episode. The patient qualifies only if one single episode was both treated with
haloperidol and worked up with a sodium level. If you want them satisfied by different episodes,
duplicate the delirium group under a second `id` and point one dependent at each copy — different ids
mean different events. This is also a cohort `"first"`/`"last"` cannot express at all, since the
qualifying episode need not be the earliest or the latest one.

**It translates**, as of `cctb`'s `"any"` support. The two dependents are emitted inside one
correlated `exists` over the delirium candidate dates, aliased `W1`, so both are bound to the same
witness - which is the shared-witness rule made concrete in the output.

---

### 8. `ccdl-example-any-chain-three-hops-draft.json` — `"any"` all the way down

Example 7 has one `"any"` anchor with two referencers, which is fan-out. This one is the other
direction: `"any"` anchors **stacked**, each hop anchored to the specific occurrence chosen at the
hop above. A clinical cascade, four groups in one group array:

```
anchor-sepsis-episode            A41.5,  "any"   ← head of the chain, no window of its own
  └── group-aki-after-sepsis     N17.0,  "any"   P0D..P7D  after that sepsis episode
        └── group-dialysis-after-aki  8-85a.0, "any"  P0D..P14D after that AKI
              └── group-hemoglobin-after-dialysis  718-7  P0D..P1D after that session
```

Read as one statement: there is a sepsis episode, followed within 7 days by an acute kidney injury,
followed within 14 days by a dialysis session, followed within a day by a haemoglobin measurement —
each "followed by" referring to the *specific* preceding occurrence, not to the earliest or latest
one on record.

What it adds over example 6:

- **Nested quantifiers, three deep.** Each `"any"` existential sits inside the one above it. The
  chain is a single nested statement, not three independent existence checks that happen to share
  names.
- **Transitive window filtering.** Per the spec's Chaining rule, a group's candidate set is the
  matches it qualifies on. So the dialysis candidates are already filtered to the AKI window, whose
  candidates are already filtered to the sepsis window. A dialysis session that followed an AKI
  which did *not* follow a sepsis episode is not a candidate for anything.
- **No `"first"`/`"last"` anywhere.** Even the head of the chain is `"any"`, so no occurrence is
  fixed in advance. Nothing in the query collapses to a date.
- **The shared-witness rule is trivial here**, because each anchor has exactly one referencer. That
  is the contrast with example 7, where two referencers on one anchor make the rule bite. Both
  behaviours come from the same rule.

This is the cohort shape that motivated `"any"` in the first place, and the one `"first"`/`"last"`
gets wrong at every hop: a patient can easily have several sepsis episodes, several AKIs and several
dialysis sessions where only one particular path through them is the qualifying one.

**Translates**, nesting one `exists` per hop: `W1` (sepsis) wraps `W2` (AKI, windowed by `W1`) wraps
`W3` (dialysis, windowed by `W2`), with the haemoglobin test innermost.

---

### 9. `ccdl-example-any-multi-clause-anchor-draft.json` — a tuple witness

The only example of a **multi-clause `"any"` anchor**. `anchor-sepsis-with-aki` is a two-clause AND —
a sepsis diagnosis and an acute kidney injury, both required — carrying `anchorOccurrence: "any"`,
referenced by a haemoglobin group within 3 days and a CRP group within 1 day.

With several clauses the witness stops being one occurrence and becomes a **tuple**, one candidate
drawn from each clause, quantified over the product of the clauses' candidate sets. The dependents'
windows come from that tuple's extremes: `minOffset` from the later of the two dates, `maxOffset`
from the earlier — the same asymmetric rule `"first"`/`"last"` multi-clause anchors already use. Both
dependents are bound to the same tuple, so the shared-witness rule applies to tuples exactly as it
does to lone occurrences.

The generated CQL nests one `exists` per clause, because Blaze accepts only single-source queries —
`from A W1, B W2` is rejected outright — so the product is expressed by nesting:

```
exists (from (<sepsis dates>) W1_1
  where exists (from (<AKI dates>) W1_2
    where Max({ W1_1, W1_2 }) + 0 hours <= Min({ W1_1, W1_2 }) + 72 hours and
      exists (... Interval[Max({ W1_1, W1_2 }) + 0 hours, Min({ W1_1, W1_2 }) + 72 hours] ...) and ...
```

That leading comparison is the bounds check. A patient whose sepsis and kidney injury lie further
apart than the offsets allow induces an inverted window, and the check turns that into a no-match
rather than an evaluation failure — Blaze rejects an inverted `Interval` outright. This is the
clearest place in the examples to see it.

### 10. `ccdl-example-all-features-draft.json` — every feature in one query

A reference file rather than a teaching one. Thirteen groups across two inclusion group arrays and
one exclusion group array, exercising every feature of the extension plus the criterion-level
features it inherits from `version: "2"`. Read examples 1 to 8 first. Come here when you need to see
how two features interact, or to copy a shape.

The cohort: adults with colonic diverticular disease who had a resection with a transfusion, and either developed a
post-operative sepsis cascade or have a matching biopsy specimen and recent follow-up labs, excluding
those on vitamin K antagonists around surgery or with chronic organ failure.

Group array 1, the main clinical path:

- `group-demographics` — gender (`concept` value filter) AND age (`quantity-comparator`, `ge` 18
  years). No anchor. Level 3 AND across two single-criterion clauses.
- `anchor-colon-diverticular-disease` — K57.3, `anchorOccurrence: "last"`, `anchorPoint: "start"`.
- `anchor-resection-with-transfusion` — a **two-clause AND anchor**, resection AND transfusion, with
  `anchorOccurrence: "first"` and `anchorPoint: "end"`.
- `group-hemoglobin-between-diagnosis-and-resection` — **two `relativeTimeRestrictions` entries**,
  each bounded on one side, intersecting into the window between the two anchors, **plus** an
  absolute `timeRestriction` on the criterion itself, which intersects with the relative window.
- `group-sepsis-after-resection` — A41.5 within 30 days of the resection, `anchorOccurrence: "any"`.
  Both a dependent and an anchor, and it has **two referencers**, so the shared-witness rule applies.
- `group-aki-after-sepsis` — N17.0 within 7 days of that sepsis episode, also `"any"`, also an anchor.
- `group-dialysis-after-aki` — the leaf of a three-hop chain.
- `group-crp-after-sepsis` — the sepsis anchor's second referencer.

Group array 2, an alternative qualifying path:

- `anchor-now` — the `now` criterion.
- `group-colon-biopsy-specimen` — a Specimen criterion carrying an **`attributeFilters`** entry of
  type `reference`, joining the sample to a diverticular disease diagnosis through the biobank extension.
- `group-followup-lab-since-resection` — references `anchor-resection-with-transfusion`, which is
  **defined in the other group array and not listed here**, and bounds the other side against `now`.

Exclusion group array:

- `group-excl-anticoagulant-around-resection` — anchored to an **inclusion-side** anchor, which is
  the cross-side reference case.
- `group-excl-organ-failure` — level 4 OR of two unanchored diagnoses.

One detail worth looking at in the output: the multi-clause anchor is consumed from both ends in the
same query. `group-hemoglobin-between-diagnosis-and-resection` bounds a `maxOffset` against it and so
resolves to `Min("AnchorDate_anchor-resection-with-transfusion")`, its earliest clause, while
`group-followup-lab-since-resection` bounds a `minOffset` and resolves to `Max(...)`, its latest. That
is the asymmetric rule from the spec, visible twice in one file.

**Translates**, at 177 lines - every feature in this document exercised in one query, verified end
to end against the real translator, including the attribute filter join, the absolute-plus-relative
window intersection and the `AgeInYears() >= 18` comparison.

---

## Feature coverage

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| OR level (more than one group array) | | | | yes | yes | | | | | yes |
| `exclusionCriteria` | | | yes | | | | | | | yes |
| `now` criterion | yes | | yes | | | | | | | yes |
| open-ended window (one offset omitted) | | | yes | yes | | yes | | | | yes |
| anchor referenced without being listed | | | | yes | yes | | | | | yes |
| cross-side anchor reference | | | yes | | | | | | | yes |
| multi-clause AND-anchor (`first`/`last`) | | | | | yes | | | | | yes |
| multiple `relativeTimeRestrictions` entries | | | | | | yes | | | | yes |
| `anchorOccurrence: "first"` | | yes | yes | yes | yes | yes | yes | | | yes |
| `anchorOccurrence: "last"` | | | | | | | | | | yes |
| `anchorOccurrence: "any"` | | | | | | | yes | yes | yes | yes |
| `anchorPoint: "end"` | | | | | | | | | | yes |
| chained anchor | | | | | | | yes | yes | | yes |
| one anchor, two referencers (shared witness) | | | | | | | yes | | yes | yes |
| chain deeper than two hops | | | | | | | | yes | | |
| multi-clause `"any"` anchor (tuple witness) | | | | | | | | | yes | |
| absolute `timeRestriction` on a windowed criterion | | | | | | | | | | yes |
| `valueFilter` | | | yes | yes | yes | | | | | yes |
| `attributeFilters` | | | | | | | | | | yes |

Every feature has at least one worked example, and example 10 has all of them except the tuple
witness, which example 9 covers on its own.

## Running them

From a built `cctb` checkout:

```sh
java -jar cli/target/cctb-cli-<version>.jar translate CQL \
  -m cql/target/mapping/cql/mapping_cql.json \
  -ct cql/target/mapping/mapping_tree.json \
  <path-to-example>.json
```

The mapping and concept-tree files are downloaded by `mvn generate-resources`. Every term code used in
these examples resolves against that snapshot, so a translation failure means a real problem, not a
missing code. All ten translate.

## Test data

Every example ships with a dataset and an expected result, so an implementation can be checked against
what the example is supposed to select rather than only against whether it translates.

```
<example>.json                        the CCDL
testdata/<example>-data.json          a FHIR transaction Bundle
testdata/<example>-expected.json      which patients it must select
```

An `expected.json` names patients rather than counting them:

```json
{
  "ccdl": "ccdl-example-any-chained-anchors-draft.json",
  "referenceDate": "2026-09-11",
  "includedPatients": ["same-episode"],
  "excludedPatients": ["no-delirium", "split"]
}
```

Counting is not enough. `same-episode` and `split` both have a delirium episode, a haloperidol
administration and a sodium measurement; the difference is whether one single episode carries both,
and a result of "1 patient" would not say which one was found. Listing the excluded patients as well
distinguishes a patient correctly rejected from one that was never in the data.

### How to use it

Load `data.json` into whatever store your implementation queries, translate the CCDL, run it, and
compare the selected patient ids against `includedPatients`. The data is plain FHIR R4 with no
profiles or extensions beyond what the examples need, so ingest it however you normally would - there
is no expectation that every engine reads a transaction Bundle directly.

Each dataset is deliberately small and built around one boundary. Every one contains at least one
patient that must **not** be selected, usually differing from an included patient by a single date, so
an implementation that ignores the time window fails rather than passing by accident.

### `referenceDate`

Dates in the bundles are absolute, but two examples are anchored to `now`
(`ccdl-example-hemoglobin-last-24h` and the respiratory-rate group in
`ccdl-with-new-time-constraint-draft`), and a fixed date cannot express "yesterday". `referenceDate`
records the day the dataset was generated. To exercise those two, shift every date in the bundle by
`today - referenceDate` when loading. The other eight use only relative-to-each-other dates and can be
loaded unchanged.

### What each dataset probes

| example | the patient that decides it |
|---|---|
| `hemoglobin-last-24h` | one observation today, one three days ago |
| `hemoglobin-24h-after-procedure` | a haemoglobin the day *before* the procedure, which a symmetric window would admit |
| `hemoglobin-between-two-anchors` | a resection *preceding* its diagnosis, so the window inverts |
| `or-scoped-anchors` | three patients qualifying through different group arrays, one through none |
| `multi-clause-anchor` | two procedures five days apart, inverting a multi-clause anchor's window |
| `any-chained-anchors` | `split`: treated after one episode, worked up after another |
| `any-chain-three-hops` | `late-episode`: qualifies only via its *second* sepsis |
| `any-multi-clause-anchor` | `two-options`: only one pairing of the tuple satisfies both windows |
| `with-new-time-constraint` | an anticoagulant without an organ failure, which does not exclude |
| `all-features` | one patient qualifying only via the second array, one surviving a partial exclusion |

Two of those are easy to get wrong by reading alone. `group-excl-organ-failure` is a single clause
with two criteria in `all-features` but two clauses in `with-new-time-constraint`, and on the
exclusion side those combine oppositely - so the two examples genuinely mean different things. And an
inverted window has to mean "selects nobody" rather than an error, which is a property of the emitted
query rather than of the language.

### Provenance

The datasets were generated from the integration tests that already evaluate these examples against a
real CQL engine, so they are data that has been run rather than data written by hand to look
plausible. Regenerating them is a side effect of running those tests with an output directory set.

## Known issues

None currently.
