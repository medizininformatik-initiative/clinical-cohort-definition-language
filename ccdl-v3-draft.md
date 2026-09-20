# Relative Time Constraints — Draft Extension

> **Status: draft, not adopted.** This document describes a proposed extension to CCDL for
> expressing time constraints between criteria (e.g. "lab value X within 72h before diagnosis Y"),
> anchored to an index event. It is written as if the design were final so it can be read and
> reviewed as a whole; the "Open Questions" section at the end lists what is genuinely still
> undecided. For a concise, rationale-free reference (just the rules and shapes), see
> [ccdl-v3-draft-tldr.md](ccdl-v3-draft-tldr.md).
>
> **This entire document is `version: "3"`, and `cctb` implements all of it.** Anchors,
> `relativeTimeRestrictions` (including multiple entries per group, intersected into one window — §4),
> `anchorOccurrence: "first"`/`"last"`/`"any"` with single- and multi-clause anchors alike,
> `anchorPoint`, the `now` criterion, the four-level structure including the OR level above the group
> array (§1–§3), the evaluation model (§6), and the translation obligations that preserve it on real
> engines (§7) are all implemented and shipped in `cctb`, the CQL translator. One shape is
> deliberately refused rather than translated: a `"first"`/`"last"` anchor chained off an `"any"`
> anchor, which would need a per-patient value computed from a witness that only exists inside a
> correlated query. `cctb` rejects it at validation with a message saying so.
>
> **One exception, added after `cctb` caught up: the uniform levels 3 and 4 of §1 are not yet
> implemented.** `cctb` still applies the `version: "2"` polarity, AND-of-OR for inclusion and
> OR-of-AND for exclusion, which is why its anchor resolution is currently correct only for
> inclusion-side anchor groups. Until it follows, an anchor group defined inside `exclusionCriteria`
> with more than one criterion is mistranslated rather than rejected.
> Everything else should be read as "this is what `cctb` does today." `version: "3"` has not been
> published or adopted anywhere yet, so there was no reason to stage it behind an intermediate,
> never-released version — the whole extension ships as one breaking change from today's adopted
> `version: "2"`. See [ccdl-tests/ccdl-v3/](ccdl-tests/ccdl-v3/) for worked examples and [Worked
> examples](#worked-examples) below.
>
> Translation targets for this extension are CQL and Delta Lake SQL only. FHIR Search is not a
> target and does not constrain this design.

## Motivation

Today's `timeRestriction` only expresses an absolute date window on a single criterion
(`afterDate`/`beforeDate`). There is no way to say that one criterion must occur near, before, or
after another criterion, or near a clinical index event (first diagnosis, admission, ventilation
start, etc.). This extension adds that, reusing the existing AND/OR structure and the existing
date-window filtering mechanism rather than introducing a second, parallel logic system.

## 1. Four fixed levels, not arbitrary nesting

`inclusionCriteria` and `exclusionCriteria` gain **two** new levels of structure relative to today's
adopted (`version: "2"`, pre-anchor) shape, not an open-ended tree. The first (what's now level 2, an
array of named **group** objects — call it a **group array**) was designed earlier, as part of the
anchor feature — it used to just be called "the top level." The second (level 1, wrapping group
arrays in OR) came later, added on top once anchors were already in place. Four fixed levels total,
and no metadata (`id`, `relativeTimeRestrictions`, `anchorOccurrence`) may attach anywhere except
level 2 — levels 3 and 4 are plain boolean grouping, nothing more:

1. **The top-level array** (`inclusionCriteria` / `exclusionCriteria` itself) — an array of
   **group arrays**. **Always combined with OR**, on both the inclusion and exclusion side (see §3
   for why — this is the level added later, on top of level 2 below it).
2. **The group array** — the array directly inside level 1 — an array of named **group** objects.
   **Always combined with AND**, on both sides. Every
   group listed in a group array is unconditionally required for that array to be satisfied — see §4 for how this interacts with `relativeTimeRestrictions`.
3. **A group's `criteria`, outer array** — **always combined with AND**, on both sides. This is a
   change from `version: "2"`, where the outer array was OR on the exclusion side. See §3 for why
   the polarity no longer alternates by side, and Compatibility for what it means for existing
   documents.
4. **A group's `criteria`, inner array** — **always combined with OR**, on both sides (the opposite
   of level 3).

```json
{
  "inclusionCriteria": [
    [
      {
        "id": "group-name",
        "relativeTimeRestrictions": [ { "...": "optional, see §4" } ],
        "anchorOccurrence": "optional, see §4 — only when this group is used as an anchor",
        "criteria": [
          [ /* level 4: OR, on both sides */ ],
          [ /* another level-3 clause */ ]
        ]
      }
    ],
    [ /* another group array — a genuine OR alternative, see §2 */ ]
  ]
}
```

`criteria` is still **always** the full two-level `[[...],[...]]` shape, unchanged from before — no
flat single-level shorthand even for one criterion with no internal AND/OR. A group array is likewise
**always** the full array-of-groups shape, even for the common case of a single group array with no
real alternative (`inclusionCriteria: [[group1, group2]]`, OR not actually in use). One shape for
tooling to parse either way, no branching on whether a given document happens to need OR.

This is still a fixed depth, not recursion: a group's internal levels 3/4 cannot themselves contain
another named, anchorable group, and a group array cannot itself contain another group array. Depth is
capped deliberately, for the same reason as originally — between a group's internal AND-of-OR and
the OR-of-AND that levels 1 and 2 provide above it (see §2), every boolean shape is already
reachable, so nothing is lost by capping it there, and a fixed, shallow shape is far easier to debug
and to translate into CQL/Delta Lake SQL than an open-ended tree.

## 2. When you actually need a second group in one array, or a second array

**A second group inside one group array** is only ever created because something needs a separate,
addressable identity to participate in an anchor relationship (§4). It is not an alternative way to
express ordinary boolean combination — that capability lives in a single group's own `criteria`
(levels 3/4), an AND of ORs on either side.

**A second group array** is created when two (or more) requirements are genuine alternatives — a
patient should qualify by satisfying *either* one, not both. A plain OR between single criteria does
not need one: "exclude if X, or exclude if Y" with no time relation between them is one group whose
`criteria` are `[[X, Y]]`, a single level-4 OR, which is what `group-excl-organ-failure` in the
worked examples is. Splitting that into two group arrays adds structure without buying anything.
Reach for a second group array when the alternatives are *compound* — each one a conjunction in its
own right, which level 3's AND cannot disjoin — or when they need genuinely different anchoring —
different anchors, or none at all on one side — which a single group's `criteria` has no way to
express, even with multiple `relativeTimeRestrictions` entries (§4): those combine via
AND-intersection onto one shared matching resource, never OR between alternatives, and whatever window results
still applies uniformly to every leaf regardless of which AND/OR branch it sits in (§6 step 5). "X
near anchor1 OR Y near anchor2" needs two group arrays, full stop — no number of entries on one
group's `relativeTimeRestrictions` gets there, because more entries only ever narrow the window, never
branch it.

## 3. Why level 2 is AND-only, and level 1 above it is OR-only

Two related but distinct questions: why level 2, the group array, stays AND-only — essentially the
original reasoning, unchanged — and why the level above it (level 1, new to this document) is OR,
uniformly, on both sides.

### Why the group array is AND-only

This argument was never really about "the top level" in the abstract; it was about anchors and their
dependents specifically, so it doesn't change just because there's now a level above the one it was
originally made about:

If one of group B's `relativeTimeRestrictions` entries anchors to group A, B can only ever be evaluated for a
patient where A's anchor date resolves — which requires A itself to be satisfied. So B implies A.
Whenever B implies A, "A OR B" is logically identical to just "A" — B never contributes anything a
disjunction wouldn't already have from A alone. Offering OR between an anchor and something anchored
to it wouldn't just be redundant, it would be misleading: it looks like a real alternative branch but
silently evaluates to nothing extra.

It goes deeper than logical redundancy, though: "B within X of A" is not even a free-standing
statement you could evaluate independently of A — it presupposes A's occurrence to have a date to
measure from at all, the way "is the thing inside the box blue" presupposes there's a box with
something in it. An anchor and something anchored to it are a parent/child pair, not peers, and OR
is a peer/sibling combinator — putting them in an OR mismatches what they structurally are to each
other, independent of what the truth table says. AND is the only combinator that doesn't lie about
that relationship, so the group array — the level an anchor and its own dependent actually live in —
stays AND-only, on both sides, for every group, not just anchor-linked pairs, keeping one uniform rule
rather than one that depends on whether a given pair happens to be anchor-linked.

**This never forbids OR between alternatives that happen to involve different anchors** — it
forbids OR between *an anchor and its own dependent* specifically, a category error regardless of
what level it happens at. Two *different* anchor-relative pathways — "lab X near diagnosis" as one
alternative, "lab Y near an unrelated procedure" as another — were never the thing this argument
ruled out. There was simply nowhere to put that OR at all, before level 1 existed.

### Why level 1, above the group array, is OR

Three independent reasons, not just "because that's what was missing":

1. **There's no alternation left to preserve.** Alternation by polarity used to exist at the group
   level (pre-anchor-feature, exclusion's top level was OR-of-AND-groups while inclusion's was
   AND-of-OR-groups) and was deliberately flattened to uniform AND when anchors were introduced,
   specifically to avoid "a rule that depends on which side you're on." This document applies that
   same reasoning to levels 3 and 4 (see "Why the polarity no longer alternates" below), so there is
   no alternating pattern anywhere left to extend outward, and the level above the group array comes
   out uniform either way.
2. **It's the semantically natural choice for both sides independently**, not just structurally
   convenient. Inclusion wants "qualifies via any of several alternative pathways." Exclusion wants
   "excluded via any of several independent disqualifying pathways" — if anything an even more
   natural fit for exclusion, since real exclusion criteria are almost always phrased as a checklist
   of alternative disqualifying reasons, rarely as "only excluded if several unrelated things are
   simultaneously true."
3. **It resolves an existing awkwardness for free.** §2 already has to carve out an exception for
   exclusion reasons that can't share a group because they need different time constraints — before
   level 1 existed, there was no way to express that at all. A uniform OR level fixes it without
   adding a second, side-dependent rule.

Nothing is lost by going uniform: "this only applies when X and Y both hold" is still fully
expressible — put X and Y in the same group array (§2). The AND case doesn't disappear, it's just
expressed at level 2 rather than needing level 1 to also alternate.

### Why the polarity no longer alternates at levels 3 and 4

Under `version: "2"` the same `criteria` meant two different things depending on which side it was
written in. `[[A], [B]]` meant `A and B` in `inclusionCriteria` and `A or B` in `exclusionCriteria`.
It now means `A and B` on both sides.

**Why it used to work that way.** Version 2 had no groups. Each side was two levels of arrays of
criteria and nothing else, so flipping the operators by side was the only way to offer both "all of
these" and "any of these". That constraint is gone.

**Why it had to change.** Most of the language only asks a group whether it matched, yes or no. An
anchor has to answer a harder question. It has to hand back a *date*, and that date comes from the
actual resources that made the group match, so the anchor rule is the one rule in the language that
reads a group's clause structure rather than only its truth value. If `[[A], [B]]` is AND, the group
is anchored by one A resource and one B resource together, and the window spans both of their dates.
If it is OR, a single resource from either clause is enough and its date is the whole answer. Same
JSON, different dates.

Under alternation, which of the two applies is fixed by the side the anchor group is *written on*.
That collides directly with what §4 makes an anchor: a referenceable object, resolved globally, whose
definition may sit in a different group array or on the opposite side from the group referencing it,
and which **must** be duplicated when two group arrays each need it without independently requiring
it. Both rules cannot hold at once. Copy one anchor definition from `inclusionCriteria` to
`exclusionCriteria`, which §4's duplication rule routinely demands, and every dependent's window
changes although not a byte of the anchor's `criteria` did. There are three ways out and each is
worse than uniformity:

- forbid cross-side `anchorRef`, removing a capability §4 is built around
- forbid cross-side duplication, leaving §4's duplication rule with an exception nothing else in the
  language has
- let a referenced anchor carry its defining side with it, making a name denote something whose
  meaning is invisible at every site that references it

Uniform AND at levels 3 and 4 removes the conflict at its source. An anchor group means the same
thing wherever in the document it is defined, so `anchorRef` stays a plain global reference and §6's
resolution rule has one form.

**What the gap looked like in practice.** §6 only ever spelled out the AND form, so an anchor defined
in `exclusionCriteria` had no stated behaviour at all, even though §4 lets you reference an anchor
from either side. `cctb` used the AND version everywhere, which broke the exclusion side both ways.
For `[[A], [B]]`, meaning `A or B`, it looked for an A date *and* a B date, so a patient who had only
A produced no anchor date and every group anchored to it quietly dropped out. For `[[A, B]]`, meaning
`A and B`, it took whichever date it could find, so a patient with only A produced an anchor date
they should never have had. Neither case raised an error. That silence is why the fix belongs in the
structure rather than in a note added to §6.

**Why not simply state both rules.** The OR form is entirely statable, and this is not an argument
that writing it was too hard. It is a genuinely second rule, though, not a special case of the first.
Under v2 polarity both inner levels flip, level 3 to OR and level 4 to AND, so an exclusion anchor's
witness is a tuple drawn from one existentially chosen clause (`[[A, B], [C]]` read as `(A and B) or
C`, per "Migrating an exclusion side"). That is the mirror image of the inclusion rule rather than a
degeneration of it, and each result §6 derives from the witness definition needs its own second form:
the decomposition equivalence, the empty-candidate-set rule, and the `"any"` product. Even granting
all of it as written, the objection to alternation is not that the missing rule is unwritable. It is
that the anchor rule would be keyed to an address rather than to anything visible in the anchor
itself, which the preceding paragraphs rule out.

**Why not an explicit operator per group.** The one alternative that survives that argument is to put
the operator on the group as a field, `"and"` or `"or"` per clause list, keying the anchor rule to a
visible property instead of to a location. It is rejected on cost, not on correctness. Every rule
that reads clause structure gains a branch, every builder gains a decision it must make on every
group, and every reader gains a field to check before the criteria can be read at all. What it buys
is that a v2 exclusion side converts with its booleans untouched, and that is worth little here,
because no v2 document parses as v3 under any circumstances (see Compatibility) so a converter always
runs and can restructure as cheaply as it can set a flag. Uniform AND deletes the case instead of
encoding it. See Open Questions for the conditions that would justify revisiting this.

**Why nothing is lost.** The OR that the exclusion side used to get from its outer array is
available at level 1, which is an OR of group arrays. `A or B` is one group whose `criteria` are
`[[A, B]]`. `(A and B) or C` is two group arrays, the first holding a group with `[[A], [B]]` and
the second a group with `[[C]]`. Level 1 exists for exactly this, so the inner levels no longer have
to provide it as well.

**What it costs.** A list of compound disqualifying reasons becomes one group array per reason,
which is more nesting than writing them as alternatives inside a single group. CCDL documents are
produced by query-building tools rather than written by hand, so a builder can present that list
however it likes and the extra nesting is never read by a person.

## 4. `relativeTimeRestrictions` and anchors

Anchors are not a special type — any group becomes an anchor simply by being referenced via
`anchorRef` from another group's `relativeTimeRestrictions`. The field is **always an array**, even
for the overwhelmingly common case of one restriction — no flat single-object shorthand, the same
"one shape for tooling to parse, no branching" rule §1 applies to `criteria`:

```json
"relativeTimeRestrictions": [
  {
    "anchorRef": "anchor-dementia-diagnosis",
    "minOffset": "-P3D",
    "maxOffset": "P0D"
  }
]
```

- `anchorRef`: id of the group whose resolved date this entry is relative to.
- `minOffset` / `maxOffset`: signed ISO 8601 durations, offset from that entry's anchor date.
  Negative = before the anchor, positive = after. At least one of the two is required per entry
  (mirrors the existing `timeRestriction` schema rule that at least one of `afterDate`/`beforeDate`
  must be present). Omitting one side leaves that side open/unbounded for that entry — see the
  worked example for both a fully-bounded window and an open-ended one.
- **Fan-out and chaining are free.** Multiple groups can set `anchorRef` to the same group id —
  one anchor, many dependents — with no extra modeling, and a group can both depend on one anchor
  and itself be the anchor for another group, as long as the reference graph stays acyclic (a
  validation-time concern, not expressible in the JSON Schema itself).
- `id` is only *required* on a group that is actually referenced as an anchor by something else;
  it's harmless (and recommended, for traceability while debugging) to set it on every group
  regardless, as the example files do.

### Multiple entries: intersected windows, one shared matching resource

`relativeTimeRestrictions` can hold more than one entry, each with its own `anchorRef` — the
motivating case is "between event A and event B" (e.g. a lab value drawn sometime between admission
and a procedure), which a single anchor can't express at all. With more than one entry, the group's
window is the **intersection** of every entry's own computed window: `windowStart = Max` of every
entry's own start bound, `windowEnd = Min` of every entry's own end bound (an entry that leaves a
side open contributes an unbounded value on that side to the `Max`/`Min` — a no-op, per the ordinary
identity of those functions).

This is deliberately a **single shared matching resource**, not "this dependent has several
independent anchor constraints": one matching resource has to fall inside *every* entry's window
simultaneously, not merely inside each one via possibly-different resources. That distinction
matters and doesn't collapse into the same thing:

- **Two separate groups**, each with a single-entry `relativeTimeRestrictions` referencing a
  different anchor, both required in the same group array (§1/§2) — two independent existence checks,
  each possibly satisfied by a *different* resource instance. Already fully expressible today, no
  new capability needed, and it's the right shape whenever the two constraints are genuinely
  independent facts rather than one shared value.
- **One group, `relativeTimeRestrictions` with two entries** — one resource that must satisfy both
  windows *at once*. Strictly stronger, and the two readings can diverge completely: if the two
  anchors are far apart in time and their windows don't overlap, the intersected reading is
  unconditionally empty (no possible timestamp satisfies both) even when the duplicated-groups
  reading would still be true (a different matching resource for each window). Reach for multiple
  entries specifically when the "between A and B, one value" reading is what's actually meant.

§6's empty-candidate-set rule extends unchanged: **every** entry's `anchorRef` must yield at least
one eligible witness for the group to match at all. A single unresolved anchor among several
correctly makes the whole group no-match, the same as it would for a lone anchor. (For hoisting
translators this means the emitted guard is the conjunction of every entry's own check rather than
just the first entry's — §7.)

### Requiredness follows group-array membership, not referenceability

`anchorRef` resolution is **global** — a dependent in one group array can reference an anchor whose
own group definition physically sits in a *different* group array, or even a different side
(inclusion vs. exclusion). Whether that anchor's own criteria are independently required is decided
entirely by which group array(s) its group is listed in as an AND member — not by whether anything
references it. A group referenced from a group array it isn't itself a member of contributes its
resolved *date* to that array's window computation; its own truth is never separately required there.

Concretely: an anchor genuinely core to one group array's own path (the index diagnosis a medication
group depends on) belongs listed inside that array, alongside its dependent — required, correctly,
for that path. A different group array that merely wants to date something relative to the *same*
underlying event, without independently requiring it (an alternative qualifying path that doesn't need
the diagnosis at all), references it by `anchorRef` without re-listing it. The asymmetry is the whole
point, and it costs nothing beyond ordinary group-array membership — no separate "is this an anchor"
flag and no registry decoupled from that membership is needed (a global registry was considered and
rejected during design: it reintroduces a confusing "which of several places does this group belong
in, and does that choice change what the query means" ambiguity that plain membership avoids).

**This does mean an anchor genuinely needed, non-required, by *two or more different* group arrays has
to be duplicated** — one copy of its criteria per array that needs it, each its own `id`. There is no
single placement that is simultaneously "in group array A" and "not required by group array A." At
the realistic scale this comes up at — a handful of alternative arrays sharing one anchor, not
open-ended fan-out — this is a tooling problem, not a structural one: a query-authoring UI can offer
"duplicate this anchor" as one action, and flag two anchor definitions that have drifted apart if
they were meant to stay identical. (Flag, not silently merge: deduplicating two identical anchor
definitions back into one id is semantics-preserving here, but **not** when either is referenced
with `anchorOccurrence: "any"`, where two ids deliberately mean two different events — see §6.)
Ordinary same-array fan-out (many dependents on one required anchor, all in the same group array)
is completely unaffected by any of this and needs no duplication — it's the same mechanism already
shipped.

### `anchorOccurrence`

Required on any group used as an anchor by at least one other group (not applicable to `now`,
which has exactly one occurrence by definition):

```json
"anchorOccurrence": "first" | "last" | "any"
```

Selects which of the anchor group's matching resources are eligible to supply the anchor date when
more than one instance could match (e.g. multiple dementia diagnoses on record). `"first"` narrows
that set to the earliest instance and `"last"` to the latest, so the anchor resolves to one date and
every dependent sees the same one. `"any"` leaves the set whole and lets the occurrence be chosen
existentially by the rest of the query, with one chosen occurrence serving every reference to that
anchor within a group array. Defined once on the anchor group itself, never per reference. All three
are the same rule under a different candidate filter — see §6, which defines the evaluation model
once and derives the three modes from it, and its dedicated `"any"` subsection.

### `anchorPoint`

```json
"anchorPoint": "start" | "end"
```

FHIR's own "when did this happen" fields are frequently a choice between a single `dateTime` and a
`Period` (`Encounter.period`, `Condition.onset[x]`, `Observation.effective[x]`,
`MedicationAdministration.effective[x]`, `Procedure.performed[x]` all work this way) — which one a
given matched instance actually has is a property of the source data, not something the query
author controls. `anchorPoint` only matters when the anchor group's matched instance turns out to
carry a `Period`: computing `anchorDate + minOffset` needs a single point in time, so the period
has to be reduced to one before offset arithmetic can run at all. Defaults to `"start"` (admission
date, onset date — usually the clinically meaningful reference point). A no-op when the matched
instance already carries a plain `dateTime` — there's nothing to choose in that case. Defined once
on the anchor group, alongside `anchorOccurrence`, so every dependent sees the same anchor point
rather than each one interpreting the same underlying event differently.

### The `now` criterion

To express "relative to today / the evaluation date" with the same mechanism, a reserved criterion
variant is introduced:

```json
{ "type": "now" }
```

Structurally a criterion (it sits inside a group's `criteria` like any other, e.g.
`"criteria": [[{"type": "now"}]]`), but carries a `type` discriminator instead of
`context`/`termCodes`, recognized as a reserved marker rather than matched against real ontology
codes. It always resolves to the evaluation timestamp and trivially "matches" every patient. A
group containing only a `now` criterion (`anchor-now` in the worked example) exists purely to be
referenced as `anchorRef`; it adds no real clinical requirement of its own. Since requiredness now
follows group-array membership (see above), such a group only needs to live in a group array where
it's actually referenced — it no longer has to sit as a vacuous, always-true member of some
universally AND'd list the way it would have before level 1 existed.

**Considered and rejected: expressing `now` via `context`/`termCodes` instead**, mirroring how the
existing `age` criterion is handled (a real SNOMED code, `424144002`, on an ordinary criterion
shape, special-cased purely in mapping data — `resourceType: "Patient"` plus a termCode-equality
check in the translator — with no schema change at all). Tempting for consistency ("one mechanism
for special-cased criteria, not two"), but it doesn't actually transfer:

- `age` special-cases a *real* ontological concept — SNOMED 424144002 genuinely means "age," the
  trick is only computing it instead of querying for it. `now` has no clinical content and refers
  to nothing about the patient at all; forcing it into `context`/`termCodes` means inventing *both*
  a fake context and a fake termCode just to satisfy a shape built for real concepts, which is a
  worse fit than age's case, not the same fit.
- **Weaker validation.** A `type` enum lets the schema itself (`oneOf`) reject a malformed/misspelled
  marker at validation time. A misspelled reserved termCode is schema-valid — it looks like an
  ordinary, merely-unmapped criterion — and only fails later, deeper in translation, with a worse
  error.
- **Namespace pollution.** A reserved termCode would sit in the same mapping table as real
  diagnoses/labs/procedures. Any concept-picker/search UI built against that table would need to
  explicitly filter it out to avoid surfacing a fabricated "now" pseudo-code next to real clinical
  concepts — a stranger anomaly than age's real-but-unusual SNOMED entry.

`type: "now"` costs an awkward `Criterion` implementation today (`NowCriterion` has to answer
`getConcept()`/`toReferencesCql` with `null`/`UnsupportedOperationException`, since those questions
don't really apply to it) — but that's the narrower, more fixable problem of the two (e.g. a
smaller marker-criterion interface that doesn't demand those methods), so it's kept.

## 5. Interaction with absolute `timeRestriction`

The existing per-criterion `timeRestriction` (`afterDate`/`beforeDate`) is unchanged and can still
be set directly on any criterion. If a criterion carries its own absolute `timeRestriction` *and*
sits in a group with one or more inherited `relativeTimeRestrictions` entries, the two bounds **intersect (AND)** —
same as any other pair of independent filters on a criterion.

## 6. Evaluation model

A group's `relativeTimeRestrictions` are evaluated in two phases per patient: resolve each entry's
anchor into a window, then filter the group's own criteria by the intersected window. Resolving the
anchor is the only genuinely new piece of logic. Everything after it reuses the existing
`timeRestriction` filtering mechanism unchanged.

The model is existential. A group carrying `relativeTimeRestrictions` matches a patient when every
entry has a **witness** — a concrete anchor occurrence, drawn from that entry's anchor group's own
matches for this patient — such that the group's own criteria match inside the intersection of the
windows those witnesses induce. One witness per entry, so the common single-entry case has exactly
one. Two quantifiers are in play and they sit on opposite sides of the restriction: the witnesses
are anchor occurrences, while §4's single shared matching resource is on the dependent side, the one
resource that must fall inside the intersected window. `anchorOccurrence` does not change any of
this. It only selects which candidates are eligible to serve as an entry's witness:

| `anchorOccurrence` | eligible witnesses |
| --- | --- |
| `"first"` | the single earliest-dated candidate |
| `"last"` | the single latest-dated candidate |
| `"any"` | every candidate |

`"first"` and `"last"` are projections of the general rule, not separate mechanisms. They narrow the
candidate set to exactly one element before the existential is evaluated, which is precisely why
they behave as a single shared anchor date and why every dependent referencing such an anchor
trivially agrees on the same reference point. `"any"` leaves the set whole and lets the rest of the
query choose. Two things follow from stating the model this way rather than treating `"any"` as an
exception, both developed below: the no-match-on-missing-anchor rule stops being a separate
normative requirement and becomes a consequence of an empty candidate set, and multi-clause anchors
stop needing a per-mode special case.

This framing changes no defaults and no behavior. `anchorOccurrence` remains required on every group
used as an anchor, with no implied value, and `"first"`/`"last"` remain the only modes `cctb`
implements. Neither does it dictate an implementation strategy: a translator SHOULD still hoist
`"first"`/`"last"` to one per-patient anchor-date value rather than emitting a one-element
existential. That hoisting is what makes §7's translation obligations necessary.

### Resolving the anchor

Steps 1–3 run once per entry in `relativeTimeRestrictions` (each entry has its own `anchorRef`, so
potentially a different anchor group each time). Step 4 then intersects the per-entry bounds — see
§4's "multiple entries" for the single-shared-resource reasoning behind intersecting rather than any
other combination.

1. **Gather candidates.** Evaluate the anchor group's own `criteria` as usual, per clause: within
   one level-4 clause the criteria are OR'd, so a candidate is every resource instance belonging to
   this patient that matches any criterion in that clause — e.g. every Condition instance coding F00
   or G30, for `anchor-dementia-diagnosis`, whose single clause holds both codes. A group with
   several clauses gathers a separate candidate set for each, since level 3 is AND and every clause
   binds (see step 3). This reads the same way on either side of the query, because §1's levels 3
   and 4 no longer alternate by polarity. "As usual"
   includes each criterion's own absolute `timeRestriction` where it has one: a resource the
   criterion does not match is not a candidate, and an anchor group can therefore be date-bounded
   in its own right (§5). If the anchor group is itself windowed relative to something else, its
   own window has already been applied at this point — see "Chaining" below.
2. **Reduce each candidate to a point (`anchorPoint`).** Take a candidate's own date as-is if it's
   a plain `dateTime`; if it's a `Period`, take `start` or `end` per the anchor group's
   `anchorPoint` (default `start`). After this step, every candidate has exactly one timestamp.
3. **Select the eligible witnesses (`anchorOccurrence`).** Filter the reduced candidates to those
   eligible under the table above: the earliest for `"first"`, the latest for `"last"`, all of them
   for `"any"`. For `"first"`/`"last"` the result is a one-element set, so everything from step 4
   onward behaves exactly like a single anchor date. For `"any"` the set is left whole and the
   witness is chosen existentially, shared across every reference to that anchor within a group
   array — see the dedicated subsection below.

   **When the anchor group has more than one clause, a witness is a tuple** — one candidate per
   clause, drawn from the product of the clauses' own eligible sets, with steps
   1–3 running per clause (`anchorOccurrence` filtering each clause's own candidates). Level 3 is
   AND on both sides (§1), so this rule has one form and an anchor group means the same thing
   wherever in the document it is defined, including inside `exclusionCriteria`. A tuple
   induces a window from both of its extremes, asymmetrically, rather than from a single collapsed
   point: `maxOffset` is measured from the **earliest** date in the tuple, `minOffset` from the
   **latest**.

   **Why this pair of bounds, and not a single collapsed point.** Two readings of "within
   `maxOffset` of a multi-clause anchor" are defensible, and this document adopts the first:

   - **Per-clause** (adopted): the dependent must fall within the offset range of *every* clause.
     The latest clause binds `minOffset`, since the group is only satisfied once its last clause
     occurs and nothing can be "at/after" it before that moment. The earliest clause binds
     `maxOffset`, since it gives the tightest ceiling.
   - **Completion**: the dependent must fall within the offset range of the moment the group was
     *established*, that is, both bounds measured from the latest clause.

   Per-clause is adopted because it makes a multi-clause anchor mean exactly what the equivalent
   decomposition already means. Split an N-clause anchor into N single-clause anchors carrying the
   same `anchorOccurrence`/`anchorPoint`, give the dependent one `relativeTimeRestrictions` entry
   per anchor, and §4's intersection rule yields `windowStart = Max(dᵢ) + minOffset` and
   `windowEnd = Min(dᵢ) + maxOffset`, the same window this rule produces. The two agree under
   `"any"` as well, since the shared-witness scope rule applied per anchor to N single-clause
   anchors quantifies over the same product as one N-clause anchor's shared tuple. Under the
   completion reading the two constructs would disagree, and splitting an anchor would silently
   change a query's meaning.

   The completion reading is not expressible by any other means, because it needs the maximum over
   clause dates as a value that varies per patient rather than an author-named index clause. It is
   recorded in Open Questions rather than offered here as a second mode.

   **Consequence for authors.** Because every clause binds, the window narrows by the spread of the
   anchor's own clauses. With `minOffset: 0` and `maxOffset: P7D` the window is
   `[latest, earliest + 7d]`, which is empty unless the clauses themselves lie within 7 days of
   each other, and a patient whose clauses are further apart matches nothing whatever the
   dependent's own dates. That is a real constraint on the anchor which the query states nowhere,
   so an anchor whose clauses are not clinically close in time needs offsets wide enough to span
   them, or should be split into separate groups. §7 covers what a translator must do to make such
   an empty window behave as no-match rather than fail.

   The tuple rule is uniform across all three modes, and nothing about it is specific to
   multi-clause anchors. Under `"first"`/`"last"` each clause contributes exactly one eligible
   candidate, so the product is a single tuple and the rule reduces to "earliest and latest across
   clauses" with nothing left to quantify — today's behavior, unchanged. Under `"any"` the product
   is quantified like any other candidate set. A single-clause anchor yields one-element tuples
   whose earliest equals its latest, reducing exactly to the original single-timestamp behavior.
   The cost, stated plainly: for a multi-clause `"any"` anchor the existential ranges over a
   product of candidate sets rather than a single set, which is a real translation and evaluation
   expense and the reason a translator may reasonably choose to support multi-clause `"any"` last.

### An empty candidate set is no-match

If step 3 leaves no eligible witness for an entry — the anchor group matched no resource for this
patient, or, for a multi-clause anchor, at least one clause matched none — the existential is false
and **the group does not match this patient.** Unconditionally, the same regardless of target query
language, and the same whether one entry's candidate set is empty or several are (§4).

This is not an additional rule layered onto the model. It is what an existential over an empty set
means, so it holds uniformly across all three `anchorOccurrence` modes, across multi-entry
`relativeTimeRestrictions`, and across multi-clause anchors, with no per-case statement needed for
any of them. It is a property of what `relativeTimeRestrictions` *means*, not a per-document or
per-restriction choice, so it is deliberately **not** exposed as a schema field (nothing to set,
nothing to forget to set, nothing that could legitimately be turned off).

Implementations do not all get this behavior for free. One that hoists `"first"`/`"last"` to a
scalar anchor date, as `cctb` does and as any sane translator will, loses the empty-set case at the
moment of hoisting: an undefined scalar flowing through offset arithmetic and interval membership
does not reliably produce no-match on real engines. Preserving the meaning defined here is then a
translation obligation, stated with its evidence in §7. An implementation that evaluated the
existential directly would owe none of it.

### `anchorOccurrence: "any"` — one shared witness per group array

Per the table in §6, `"any"` is the mode that leaves the candidate set whole. `"first"`/`"last"`
narrow it to a single element, so the witness is fixed before any dependent is evaluated and every
reference to the anchor trivially agrees on it. `"any"` defers the choice to the rest of the query.
That is what makes it more expressive, and it is also what makes the following scope question arise
at all: `"any"` is the only mode in which two references to one anchor could, in principle,
disagree about which occurrence they mean.

**Why this is needed:** chains longer than one hop. Consider "delirium within 30 days after a
dementia diagnosis, followed by an antipsychotic prescription within 3 days after *that specific*
delirium episode." With `delirium` anchored to `diagnosis` and then itself referenced by
`antipsychotic` via `"first"`/`"last"`, `delirium` collapses to one timestamp before
`antipsychotic`'s window is computed from it — but a patient can have several delirium episodes
following the diagnosis, only one of which is actually followed by an antipsychotic within 3 days,
and it need not be the first or the last one. Neither `"first"` nor `"last"` gets this patient right,
regardless of which is chosen. `anchorOccurrence: "any"` on `delirium` is the correct reading: some
delirium episode, in the diagnosis window, has an antipsychotic within 3 days of it.

**The scope rule.** Everything subtle about `"any"` is in the answer to "which occurrence, for
whom" when more than one group references the same anchor. State it to authors loudly, because it
is the whole semantics:

> Within one group array, every `relativeTimeRestrictions` entry naming the same `anchorRef` is
> satisfied by the **same** anchor instance. One `anchorRef`, one event — always, in all three
> `anchorOccurrence` modes.

Formally, for an `"any"` anchor `A` referenced by groups `B` and `C` in the same group array, the
array requires

```
∃a ∈ candidates(A): φ_B(a) ∧ φ_C(a)
```

— one witness `a` serving both references — and **not** `(∃a: φ_B(a)) ∧ (∃a: φ_C(a))`, which would
allow `B` and `C` to be satisfied by two different instances of `A` while still calling them by one
name. That second, per-reference-independent reading is the obvious weaker alternative, and it was
considered and rejected during design. It is wrong for exactly the reason the naming mechanism
exists at all: if two groups both reference `anchor-delirium` and may each pick a different delirium
episode, the name has silently stopped denoting an event. The shared reading is also strictly
stronger — a shared witness is a witness for each reference separately, so shared ⟹ independent and
not the reverse — so it can never include a patient the weaker reading would exclude. Where only one
group references the anchor (the chain case above), the two readings coincide and the distinction
costs nothing.

The scope is the **group array**, because group arrays are OR-alternatives evaluated independently
of one another (§1–§3): each is its own truth evaluation, so it is the natural scope for the
quantifier. References from two different group arrays never coordinate on a witness, even when
they name the same anchor id — nothing about evaluating one alternative constrains another.

**Escape hatch: duplicate the anchor.** When genuinely independent witnesses *are* what's meant —
"some delirium episode was followed by an antipsychotic, and some delirium episode, not necessarily
the same one, was followed by a restraint order" — write the anchor twice: identical `criteria`,
two different `id`s, each dependent pointing at its own copy. This is §4's duplication rule applied
unchanged (**different ids = different events, same id = same event**), so it needs no new syntax,
and it has no side effect on requiredness: two copies with identical criteria are true on exactly
the same patients as one copy.

Note the direction this makes the default. Duplication recovers the independent reading from the
shared one; nothing recovers the shared reading from the independent one, which would need a new
correlation marker meaning "these two references must hit the same event." Defaulting to the
stronger reading is what keeps both expressible.

One consequence for tooling, worth naming because §4 recommends the opposite for the
`"first"`/`"last"` case: an authoring tool **MUST NOT** automatically merge two identical anchor
definitions into a single id when either is referenced with `"any"`. Under `"first"`/`"last"` that
merge is semantics-preserving (identical criteria resolve to identical dates); under `"any"` it
imposes a shared witness the author deliberately avoided, and changes which patients match.
Flagging drifted near-duplicates for human review stays fine; silently deduplicating them does not.

**Interactions with the rest of the model:**

- **Multi-clause anchors are supported, at a cost.** A multi-clause `"any"` anchor's witness is a
  tuple, one candidate per clause, and the window it induces comes from the tuple's extremes:
  `maxOffset` from the earliest member, `minOffset` from the latest. That is the same asymmetric
  rule `"first"`/`"last"` already use for multi-clause anchors (step 3), not a new one. The
  shared-witness scope rule applies to the tuple as a whole, so every reference to such an anchor
  within one group array agrees on the same tuple. The cost is combinatorial: the existential ranges
  over the product of the clauses' candidate sets rather than over a single set, which is worth
  weighing before reaching for a multi-clause `"any"` anchor where a single-clause one would do.
- **No null-guard.** An empty candidate set already makes the existential false (§6, "An empty
  candidate set is no-match"), and an `"any"` reference is never hoisted to a scalar date, so the
  guard §7 obliges hoisting implementations to emit has nothing to guard here. §7 states that as a
  MUST NOT.
- **Chaining composes.** A group that is itself windowed relative to one anchor can be referenced
  as an `"any"` anchor by something further downstream with no special case: step 1 gathers that
  group's own qualifying, window-filtered matches as the candidate set, exactly as the Chaining
  subsection below specifies for every mode.

**Translation shape.** `"first"`/`"last"` hoist to one per-patient anchor-date value that every
dependent shares (`cctb`'s `AnchorDate_...` define). An `"any"` reference cannot be hoisted that
way at all, and — following the scope rule — it is also not one existential per reference site. It
is **one** correlated existential over the anchor's candidate set, wrapping a conjunction of the
window tests contributed by *every* group in that array which references the anchor: structurally
`exists (candidates(A) a where φ_B(a) and φ_C(a))` as a nested `exists ... such that ...` (CQL) or
correlated join (SQL).

This couples the translation of sibling groups, which is a real architectural cost and is stated
here rather than discovered during implementation: a group carrying an `"any"` entry can no longer
be translated in isolation, because its own output depends on which other groups in the same array
reference the same anchor. A group referencing that anchor from a *different* group array is not
part of the conjunction and gets its own separate existential, per the scope rule. This is a
distinct translation path from the hoisted-anchor-date one described in §7, not a variant of it.

**Status:** implemented in `cctb`, single- and multi-clause, including chains of `"any"` anchors and
the shared-witness coupling across sibling referencers. The one shape `cctb` refuses is a
`"first"`/`"last"` anchor chained off an `"any"` one, which it rejects at validation - such an anchor
would have to compute its per-patient date from a witness that only exists inside a correlated query.

### Chaining: an anchor's candidates are its own qualifying matches

A group can be both a dependent and an anchor at once (§4, "fan-out and chaining are free"). When a
chained group is used as an anchor, step 1 gathers the matches on which that group **actually
qualifies**, meaning its own `relativeTimeRestrictions` window has already been applied. A resource
that matches the chained group's criteria but falls outside that group's own window is not a
candidate and cannot serve as a witness for anything downstream.

This is the only reading consistent with the rest of the model. "Delirium within 30 days of the
diagnosis, antipsychotic within 3 days of that delirium" cannot mean that any delirium on record,
including one from five years before the diagnosis, is eligible to date the antipsychotic window.
The window on the middle group is part of what makes an occurrence of it an occurrence *of that
group*, and the anchor mechanism resolves groups, not bare criteria.

Under `"any"` the quantifiers nest rather than interact. A downstream `"any"` reference quantifies
over the intermediate group's already-window-filtered matches, and the shared-witness scope rule
applies to each anchor id separately, so a chain of `"any"` anchors shares one witness per id per
group array without any of them constraining another id's choice. Worked through three levels deep in
`ccdl-example-any-chain-three-hops-draft.json` (see Worked examples).

**`cctb` implements this.** `Group.resolveAnchorDates` computes the group's own window first and
passes it down through `aggregateClauseDates` into `resolveClauseDate`, so the emitted candidate
query carries the window predicate. For a chained anchor the generated CQL reads
`Min((from [Condition: Code 'N17.0' ...] C where ToDate(C.recordedDate as dateTime) in
Interval["AnchorDate_<upstream>" + 0 hours, "AnchorDate_<upstream>" + 168 hours] ...))`, which is the
rule above.

The §7 null-guard travels down the same path: `Group.resolveAnchorDates` ANDs the upstream window's
guard into the chained anchor's own, so an anchor that fails to resolve anywhere up the chain forces
no-match at every point below it rather than leaving a downstream window unbounded. Verified against
real Blaze by `EvaluationIT.evaluateChainedAnchorGuardPropagatesFromHeadOfChain`, which translates
the last link of a three-group chain in isolation so nothing but the propagated guard can exclude a
patient missing the head.

### Applying the window

Steps 4–6 resume from step 3, once per group rather than per entry, and are unchanged by everything
between: whichever witness a mode selects, it supplies a date, and the rest of the model does not
care how it was chosen.

4. **Compute the bound.** Each entry in `relativeTimeRestrictions` computes its own bound the same
   way as before — `entryStart = entryAnchorDate + entry.minOffset` (or unbounded, if absent);
   `entryEnd = entryAnchorDate + entry.maxOffset` (or unbounded, if absent) — then the group's actual
   `windowStart`/`windowEnd` is the **intersection** across every entry: `windowStart = Max` of every
   `entryStart`, `windowEnd = Min` of every `entryEnd` (§4). For the single-entry case (still the
   common one) this is exactly `Max`/`Min` of one value each, i.e. that value itself — nothing
   changes versus today's behavior.
5. **Distribute.** Apply `[windowStart, windowEnd]` to every leaf criterion in the dependent
   group's `criteria` tree — regardless of whether it sits under the AND or the OR branch —
   exactly as an ordinary `timeRestriction` would be applied to a single criterion, including
   reusing the existing overlap-sufficiency rule for criteria whose own date is a `Period` rather
   than a point (see the open question below on whether overlap is the right default at narrow
   window widths).
6. **Evaluate.** Run the dependent group's normal AND/OR logic (levels 3/4) over the now
   date-filtered candidates, exactly as group matching already works today.

## 7. Translation obligations

§6 defines what a group carrying `relativeTimeRestrictions` means. This section states what a
translator must do to preserve that meaning on real engines. The two are deliberately separated:
nothing below is language semantics, none of it is observable in a CCDL document, and an
implementation that evaluated §6's existential directly rather than hoisting would owe none of it.
The obligations exist because every practical translator hoists `"first"`/`"last"` to a single
per-patient anchor-date value, which is the right thing to do for performance and which discards the
empty-candidate-set case in the process.

For orientation, the expected shape in each supported target: in CQL, §6's window maps onto
`Interval`/`before`/`after`/`within` directly. In Delta Lake SQL, §6 steps 1–4 become a per-patient
anchor-date CTE (`GROUP BY` patient with `MIN`/`MAX` for `"first"`/`"last"`), joined against each
criterion's table scan with the computed date-range predicate from step 5. Both are standard
analytical patterns, and both are hoisting implementations, so both incur everything below.

### Preserving no-match on an empty candidate set

A translator that hoists an anchor to a scalar date **MUST NOT** satisfy §6's empty-set rule by
relying on the target language's own null/undefined-value propagation through offset arithmetic and
interval-membership checks — that is, by assuming `undefinedAnchorDate + offset` and "is this date
within `[undefined, undefined]`" naturally propagate to false. That propagation is not guaranteed by
every target engine.

A translator **MUST** instead emit an explicit guard around any window-filtered criterion (an
explicit "anchor date is not null" check combined with the window-membership test) rather than
depending on implicit propagation, and **MUST** verify this against a real instance of its target
engine. Reasoning about the target language's specification is not sufficient on its own, per the
evidence below. With multiple entries the guard is the conjunction of every entry's own check (§4),
since a single unresolved anchor among several must make the whole group no-match.

The obligation is scoped to hoisted anchors, which today means `"first"`/`"last"`. An `"any"`
reference is never hoisted — it compiles to a correlated existential, which is natively false on an
empty candidate set — so a conformant translator **MUST NOT** emit a date-null guard for an `"any"`
reference. There is no anchor date there to guard. It **MUST** instead ensure the existential itself
is correctly false on zero candidates, which every standard `exists`/correlated-join construct
already guarantees by definition.

### Why this is stated as an obligation rather than assumed

Both of the following were confirmed empirically against Blaze 0.34, a real, spec-conformant CQL
engine. They are recorded here because reasoning from the CQL specification alone would have
produced a translator that is wrong on a live engine, twice.

- **Undefined anchor dates do not propagate to no-match.** Blaze silently treats the window as
  unbounded instead, which is the worse of the two possible failure modes: silent wrong inclusion
  rather than a loud error.
- **`Min`/`Max` over a list ignore null elements rather than propagating them.** For a multi-clause
  AND-anchor, an aggregate-level null check therefore proves only that *at least one* clause
  resolved, not that all of them did, so the guard must check each clause's own resolved date
  individually. A first implementation of that per-clause check used a nested
  `not exists (... where D is null)` query, and Blaze 0.34 fails to detect a null list element
  sourced from a `Min`/`Max(retrieve)` aggregate through that specific query shape, though it
  detects a literal null correctly.

### Making an inverted window no-match

A group's window can come out inverted — `windowStart` later than `windowEnd` — whenever two
independently resolved dates bound opposite ends of it. Two constructs in this document do that:
multiple `relativeTimeRestrictions` entries, whose intersection takes its start from one anchor and
its end from another (§4); and a multi-clause anchor, whose `minOffset` is measured from the latest
clause and `maxOffset` from the earliest (§6 step 3). "Between the diagnosis and the procedure" is
inverted for a patient whose procedure came first, and a multi-clause anchor's window is inverted
whenever its clauses lie further apart than the offsets allow.

Semantically that is settled and needs no rule of its own: no timestamp can fall inside such a
window, so the group does not match. A translator **MUST** ensure the emitted query behaves that
way, and **MUST NOT** assume the target engine reaches it on its own.

Confirmed empirically, in the same spirit as the null-guard above: Blaze rejects an inverted
`Interval` outright rather than treating it as empty, failing the entire evaluation with "Invalid
interval bounds" — for interval membership and for `overlaps` alike. That is worse than a wrong
answer, because one patient whose dates happen to invert takes down the whole cohort query. The same
bounds expressed as `>= and <=` comparisons evaluate to false as expected, and an explicit
`windowStart <= windowEnd` check placed ahead of the membership test short-circuits before the
interval is ever built.

`cctb` emits that check as part of the window's guard, and only where a window can actually invert. A
single entry against a single-clause anchor cannot: both of its bounds are the same resolved date
plus a constant, so the window is inverted only if `minOffset` exceeds `maxOffset`, which is an
authoring mistake rather than a property of the data.

### How `cctb` implements it

`Group.Window` carries an explicit guard alongside the computed interval, AND'd in once after the
group's own criteria are fully combined rather than per leaf criterion. The guard is the conjunction
of every entry's own check, plus the `windowStart <= windowEnd` bounds check above wherever
`Group.canInvert` reports that this group's window can invert. The per-clause check for multi-clause
AND-anchors uses direct list-index access (`list[i] is not null`), confirmed to work correctly on
Blaze where the nested-query shape above does not.

An `"any"` reference is never hoisted, so it carries no date-null guard at all - the correlated
`exists` is natively false on an empty candidate set. It does still carry the bounds check when its
anchor is multi-clause, since a tuple witness whose members lie far apart inverts the window exactly
as a multi-clause `"first"`/`"last"` anchor does.

The guard also travels along the chaining path: `Group.resolveAnchorDates` ANDs the upstream window's
guard into a chained anchor's own, so an anchor that fails to resolve anywhere up the chain forces
no-match at every point below it rather than leaving a downstream window unbounded.

## Compatibility

This draft is **not valid** against the current schema (`version` const `"2"`): restructuring
group arrays into objects (`{id, criteria, ...}`) fails validation against `$defs/criterion` for
the same reason a bare object without `context`/`termCodes` always would. Per the project's stated
versioning policy (the `$id`/`version` only changes on breaking releases), this is a genuine breaking
change, not an additive one.

- **`version: "3"`** — everything in this document, all at once: anchors,
`relativeTimeRestrictions` as a genuine array (§4, including multiple entries per group),
`anchorOccurrence`/`anchorPoint`, the `now` criterion, the evaluation model (§6) with its
translation obligations (§7), and the four-level structure with the OR level above the group array
(§1–§3). `inclusionCriteria`/`exclusionCriteria` are always the full `[[group,...],[group,...]]`
shape described in §1, even for the common case of a single group array with no real OR
alternative in use. `version: "3"` has not been published or adopted anywhere yet, so there was no
reason to split this behind an intermediate, never-released version — it ships as one step from
today's adopted `"2"`.

### Migrating an exclusion side

Levels 3 and 4 no longer alternate by side (§1, §3), so a `version: "2"` exclusion group means
something different read as `version: "3"`. This cannot be missed by accident: a v2 document does
not parse as v3 at all, because its criteria arrays hold bare criteria where v3 requires group
objects, so every document passes through a converter regardless. The conversion of the boolean
content is mechanical, and there is one rule for it.

**Split at level 1. Never distribute.** Each clause of a v2 exclusion group's outer array is one
disqualifying alternative, so each becomes its own group array. A clause's own criteria were AND'd,
so they become that group's clauses, one criterion each. `[[A, B], [C]]`, which read as
`(A and B) or C`, becomes two group arrays, the first holding a group with `criteria` `[[A], [B]]`
and the second a group with `criteria` `[[C]]`. A single-clause exclusion group, the common case,
becomes one group array with one group, and a v2 group of the shape `[[X], [Y]]`, which read as
`X or Y`, collapses to the single clause `[[X, Y]]`.

Distributing into conjunctive normal form inside one group is also exact and is occasionally what
you want, specifically when the alternatives must share one group's `relativeTimeRestrictions` or
`anchorOccurrence`. It should never be generated automatically. It duplicates criteria
multiplicatively, and a builder that stores it has to redistribute on load, which does not round
trip and silently regroups the author's alternatives. Where alternatives in separate group arrays
share a time constraint, repeat the `relativeTimeRestrictions` entry in each. The anchor group
itself stays single and is referenced by `id` from all of them (§4).

## Worked examples

All ten live in [ccdl-tests/ccdl-v3/](ccdl-tests/ccdl-v3/), all `version: "3"`, with a reading
guide in [ccdl-tests/ccdl-v3/README.md](ccdl-tests/ccdl-v3/README.md). Every one of them
translates through `cctb`.

**[ccdl-with-new-time-constraint-draft.json](ccdl-tests/ccdl-v3/ccdl-with-new-time-constraint-draft.json)**.
Defines a cohort of female patients with a first dementia diagnosis (F00 or G30) as the index event,
in a single group array (no OR alternatives in use), and:

- `group-infection-signs-before-diagnosis` — `(CRP OR leukocytes) AND heart rate`, all within
  the 3 days up to the diagnosis. Demonstrates level 3 (AND) and level 4 (OR) both in use inside
  one time-restricted group.
- `group-donepezil-after-diagnosis` — Donepezil started within 30 days after the diagnosis.
- `group-weight-since-diagnosis-window` — a body-weight measurement recorded from 7 days before the
  diagnosis onward, with no upper bound (`minOffset` only, `maxOffset` omitted).
- `anchor-now` / `group-respiratory-rate-since-now` — a second, independent anchor ("today"), used
  to require a respiratory-rate measurement in the last 7 days, showing an anchor that isn't a
  clinical event.
- `group-excl-anticoagulant-after-diagnosis` — an exclusion criterion anchored to the same
  diagnosis: patients who received an anticoagulant within 2 days after it are excluded.
- `group-excl-organ-failure` — `chronic renal failure OR hepatic failure`, with **no** anchoring,
  showing the §2 rule: an OR of independent exclusion reasons with no anchoring difference between
  them stays inside one group, rather than being split across group arrays for no reason.

**[ccdl-example-or-scoped-anchors-draft.json](ccdl-tests/ccdl-v3/ccdl-example-or-scoped-anchors-draft.json)**.
Illustrates §1–§3, the OR level above the group array. Three group arrays, OR'd:

- Group array 1 — `group-gender` AND `group-crp-standalone`. Plain AND, no anchor at all.
- Group array 2 — `anchor-dementia-diagnosis` AND `group-donepezil-after-diagnosis`, both listed and
  required together in the same array. Demonstrates a group array where an anchor is genuinely,
  itself, a required member of that path.
- Group array 3 — `group-weight-since-diagnosis-window` alone, referencing group array 2's *same*
  anchor by id without re-listing it. Demonstrates the asymmetric case from §4: required in group
  array 2's path, merely a date source — not independently required — in group array 3's. Note that
  this asymmetry is invisible in the generated CQL for a single-clause anchor, because the §7
  null-guard `"AnchorDate_..." is not null` is already equivalent to "the anchor group matched", and
  the redundant anchor-own-criteria optimization therefore drops the separate check. The two cases
  diverge in output for a multi-clause anchor, where the guard checks each clause individually.

**[ccdl-example-any-chained-anchors-draft.json](ccdl-tests/ccdl-v3/ccdl-example-any-chained-anchors-draft.json)**.
The only example of `anchorOccurrence: "any"` and of a chained anchor. One group array, four groups,
a two-hop chain: a first dementia diagnosis anchors a delirium episode within 30 days, and that
episode in turn anchors two things of its own.

- `anchor-dementia-diagnosis` — `"first"`, the ordinary index event at the head of the chain.
- `group-delirium-after-diagnosis` — F05 within 30 days after the diagnosis, `anchorOccurrence:
  "any"`. **Both a dependent and an anchor**, which is what makes this the chaining example: per
  §6's "Chaining" subsection, the candidate set the two groups below resolve against is this group's
  already-window-filtered matches, so a delirium outside the 30-day window cannot date anything.
- `group-haloperidol-after-delirium` — haloperidol within 3 days after the delirium episode.
- `group-sodium-around-delirium` — a serum sodium measured within a day either side of it.

The last two are the point of the example. Both name `group-delirium-after-diagnosis` as their
anchor inside one group array, so §6's scope rule binds them to the **same** delirium episode: the
patient qualifies only if one single episode was both treated with haloperidol and worked up with a
sodium level. Under the rejected per-reference-independent reading, a mild episode treated with
haloperidol plus an unrelated later episode with a sodium level would have been enough. To express
*that* instead, duplicate the delirium group under a second `id` and point one dependent at each
copy, per §6's escape hatch.

Also the reason `"first"`/`"last"` cannot express this cohort at all: collapsing the delirium group
to one episode before evaluating the two dependents gets patients wrong whichever end is chosen,
since the qualifying episode need not be the earliest or the latest.

**Translates**, as of `cctb`'s `"any"` support. The group array compiles to a single `exists` over
the window-filtered delirium candidate dates, aliased `W1`, with both dependents evaluated inside it
against that one alias. That is the §6 scope rule made concrete in the output: the haloperidol check
and the sodium check see the same bound occurrence rather than the candidate set independently.
`WorkedExampleIT.anyChainedAnchors` evaluates it against a real engine, where `split`, a patient
treated after one episode and worked up after another, is correctly excluded.

**[ccdl-example-hemoglobin-last-24h.json](ccdl-tests/ccdl-v3/ccdl-example-hemoglobin-last-24h.json)**.
The minimal case: one group array, `anchor-now` plus a single dependent group requiring a hemoglobin
measurement in the last 24 hours. No OR, no fan-out, no multi-clause anchor — the smallest complete
`relativeTimeRestrictions` example, useful as a quickstart.

**[ccdl-example-hemoglobin-24h-after-procedure.json](ccdl-tests/ccdl-v3/ccdl-example-hemoglobin-24h-after-procedure.json)**.
The same minimal shape as the file above, anchored to a clinical event rather than to the clock: one
group array, a single-clause `anchor-procedure` with `anchorOccurrence: "first"`, and one dependent
group requiring a hemoglobin measurement in the 24 hours after it. The smallest example in which §7's
null-anchor requirement is observable — `anchor-now` always resolves, so a real retrieve is needed
before the guard can fail on anyone.

**[ccdl-example-multi-clause-anchor.json](ccdl-tests/ccdl-v3/ccdl-example-multi-clause-anchor.json)**.
Two group arrays sharing one procedure anchor, `anchor-procedure` — itself a two-clause AND of two
OPS codes for the same procedure, demonstrating §6 step 3's asymmetric multi-clause anchor bounds.
Group array 1 lists the anchor as a required member alongside a dependent hemoglobin-and-diagnosis
group, and alongside `group-gender`, an ordinary unanchored group AND'd in as a plain demographic
filter — the reminder that anchored and unanchored groups mix freely inside one group array. Group
array 2 references the *same* anchor by id, with a differently-coded dependent group, without
re-listing it — a second illustration of the §4 asymmetric-requiredness pattern, this time paired
with a genuinely multi-clause anchor rather than the single-clause one above.

**[ccdl-example-any-chain-three-hops-draft.json](ccdl-tests/ccdl-v3/ccdl-example-any-chain-three-hops-draft.json)**.
The deep-chain counterpart to the example above: `"any"` anchors **stacked**, rather than one `"any"`
anchor with two referencers. Four groups in one group array, a clinical cascade —
`anchor-sepsis-episode` (A41.5, `"any"`, itself unwindowed) anchors `group-aki-after-sepsis` (N17.0,
`"any"`, within 7 days), which anchors `group-dialysis-after-aki` (8-85a.0, `"any"`, within 14 days),
which anchors `group-hemoglobin-after-dialysis` (718-7, within a day). Each hop refers to the
specific occurrence chosen at the hop above, so the whole query is one nested existential three
levels deep, and §6's Chaining rule applies transitively: the dialysis candidates are already
filtered to the AKI window, whose candidates are already filtered to the sepsis window. Note that no
group here fixes an occurrence in advance, not even the head of the chain, and that the shared-witness
scope rule is trivially satisfied because each anchor has exactly one referencer — the contrast with
the two-referencer example above, both falling out of the same rule. **Translates**, nesting one
`exists` per hop: `W1` (the sepsis episode) wraps `W2` (the AKI, windowed by `W1`) wraps `W3` (the
dialysis session, windowed by `W2`), with the haemoglobin check innermost. Covered end to end by
`WorkedExampleIT.anyChainThreeHops`, where `late-episode` qualifies only through its second sepsis.

**[ccdl-example-any-multi-clause-anchor-draft.json](ccdl-tests/ccdl-v3/ccdl-example-any-multi-clause-anchor-draft.json)**.
The only example of a **multi-clause `"any"` anchor**, where the witness is a tuple rather than a
single occurrence. `anchor-sepsis-with-aki` is a two-clause AND — a sepsis diagnosis and an acute
kidney injury, both required — with `anchorOccurrence: "any"`, referenced by a haemoglobin group
within 3 days and a CRP group within 1 day. A witness is one candidate drawn from each clause, and the
dependents' windows come from that tuple's extremes: `minOffset` from the later of the two dates,
`maxOffset` from the earlier. Both dependents are bound to the same tuple, so this is the
shared-witness rule applied to a tuple rather than to a lone occurrence.

It is also the clearest place to see the §7 bounds check in the output: a patient whose sepsis and
kidney injury lie more than three days apart induces an inverted window, and the emitted
`Max({...}) + 0 hours <= Min({...}) + 72 hours` conjunct is what turns that into a no-match instead
of an evaluation failure.

**[ccdl-example-hemoglobin-between-two-anchors.json](ccdl-tests/ccdl-v3/ccdl-example-hemoglobin-between-two-anchors.json)**.
The "between event A and event B" pattern from §4, and the only example where a single group carries
more than one `relativeTimeRestrictions` entry. A haemoglobin measured somewhere between a colonic
diverticular disease diagnosis (`anchor-colon-diverticular-disease`, K57.3) and the resection
(`anchor-colon-resection`, 5-455.3), which is the pre-operative anaemia window. The dependent
group's two entries each name a different anchor and each bound **one side only** — `minOffset`
against the diagnosis, `maxOffset` against the resection — so the intersection of the two windows is
exactly the interval between the two events. The generated CQL shows the §6 step 4 rule literally,
`Interval[Max({anchorA + 0 hours, @0001-01-01T}), Min({@9999-12-31T, anchorB + 0 hours})]`, with the
unbounded side of each entry contributing the identity element. It also illustrates why this is not
the same query as two separate single-entry groups: those would be satisfied by two *different*
haemoglobin values, whereas the intersected window demands one value inside both.

**[ccdl-example-all-features-draft.json](ccdl-tests/ccdl-v3/ccdl-example-all-features-draft.json)**.
A reference file rather than a teaching one: thirteen groups across two inclusion group arrays and
one exclusion group array, exercising every construct in this document at once, plus the
criterion-level `valueFilter`, `attributeFilters` and absolute `timeRestriction` inherited from
`version: "2"`. It is the only example carrying `anchorOccurrence: "last"`, `anchorPoint: "end"`, an
absolute `timeRestriction` on a criterion that also sits in a relative window (§5), and an
`attributeFilters` entry. It also shows the §6 step 3 asymmetric multi-clause rule consumed from
both ends in one query: a group bounding `maxOffset` against `anchor-resection-with-transfusion`
resolves to that anchor's earliest clause date, while a group bounding `minOffset` against the same
anchor resolves to its latest. It translates at 177 lines of CQL — every construct in this document
verified end to end against the real translator in one query.

## Open Questions (not yet decided)

- **Overlap vs. containment for narrow relative windows.** §6 step 5 inherits the existing
  `timeRestriction` rule that overlap between a criterion's own interval and the window is
  sufficient. That's reasonable for the looser windows the absolute case was designed around, but
  at the 72h-scale windows relative restrictions are meant for, a `Period`-valued criterion that
  merely creeps into the edge of the window may be too lenient a match for some use cases, versus
  others where overlap is exactly what's wanted. Not yet decided whether the single inherited
  default is enough, or whether a configurable match mode (`overlaps` / `contains` /
  `starts-within` / `ends-within`) is needed.
- **A "completion" reading for multi-clause anchors.** §6 step 3 adopts the per-clause reading, in
  which every clause of a multi-clause anchor binds the window. The alternative is to measure both
  bounds from the moment the anchor group was *established*, i.e. from its latest clause, so that
  "within 7 days of the anchor" does not additionally require the anchor's own clauses to lie within
  7 days of each other. Unlike per-clause, it is not reachable by decomposing the anchor, since the
  index clause would have to be whichever one happens to be later for each patient rather than one
  the author names up front. Not offered as a second mode: per-clause is strictly stronger, so it
  never admits a patient the completion reading would reject, and no use case has asked for the
  weaker one yet. Worth revisiting if authors turn out to write multi-clause anchors whose clauses
  are routinely further apart than the dependent's offsets.
- **Signed duration format — resolved for CQL.** `"-P3D"`-style signed ISO 8601, matching
  `java.time.Duration.parse`, is what the CQL translation path actually parses `minOffset`/
  `maxOffset` with, confirming the convention this draft assumed. One implementation detail worth
  carrying forward into the schema/tooling discussion: `Duration` is normalized to whole hours
  before being printed into CQL offset arithmetic (`DateTime + n hours`), sidestepping
  calendar-day/DST ambiguity — sub-hour offsets (e.g. `"PT30M"`) would truncate to zero under that
  scheme. Fine for the offsets this feature targets (hours-to-days scale), but worth flagging if a
  future use case needs sub-hour precision. Still unconfirmed for the Delta Lake SQL layer, which
  isn't implemented yet.

**Retired (resolved):**

- ~~An explicit `and`/`or` operator field per group~~ — considered while deciding levels 3 and 4,
  rejected in §3. It is the only alternative to uniform AND that survives the cross-side reference
  argument, because it keys the anchor rule to a visible property of the group rather than to the
  side the group happens to be written on. Rejected on cost: a branch in every rule that reads clause
  structure, a decision every builder must make on every group, and a field every reader must check
  before the criteria can be read. Its one benefit, v2 exclusion sides converting with their booleans
  untouched, is worth little when no v2 document parses as v3 anyway and a converter always runs.
  Worth revisiting only if a use case appears that genuinely needs OR *inside* a group and cannot use
  the level-1 OR instead — the candidate shape is alternatives that must share one group's
  `relativeTimeRestrictions` or `anchorOccurrence`, which today has to be written by distributing
  into conjunctive normal form (see "Migrating an exclusion side").
- ~~OR across differently-windowed siblings of the same anchor~~ — resolved by the level-1 OR
  wrapping the group array (§1, §3). Two branches needing different offsets off the same (or
  different) anchors are now just two group arrays.
- ~~Where trivial anchors like `now` should live~~ — resolved by §4's "requiredness follows
  group-array membership" rule. A `now`-only group only needs to live in whichever group array
  actually references it; it no longer has to sit as a vacuous member of a single,
  universally-required list.
- ~~The null-guard is not applied along `cctb`'s chaining path~~ — fixed in `cctb`.
  `Group.resolveAnchorDates` now ANDs the upstream window's guard into the chained anchor's own, so
  an unresolved anchor anywhere up the chain forces no-match at every point below it instead of
  leaving the downstream window unbounded. Never an open design question, only a translation
  obligation left unmet; see §6 Chaining and §7.
- ~~`anchorOccurrence: "any"` is unimplemented in `cctb`~~ — implemented, single- and multi-clause,
  including chains and the shared-witness coupling, and covered by
  `EvaluationIT.evaluateAnyAnchorRequiresOneSharedWitness`. One shape is refused at validation
  rather than translated: a `"first"`/`"last"` anchor chained off an `"any"` anchor (see the status
  banner). The only `"any"`-adjacent item still undecided is the window match mode above, which is
  not specific to `"any"`.
- ~~Multiple anchors per dependent group~~ — resolved by §4's "multiple entries" subsection: a
  group's `relativeTimeRestrictions` is a list, more than one entry AND-intersects their windows
  onto a single shared matching resource, which is exactly the "between event A and event B" pattern
  this question was about. Explicitly a different mechanism from §1–§3's OR between group arrays
  (intersection of anchors on one group, not alternation between independently-anchored branches) —
  the two don't overlap or substitute for each other, both are now decided design and both
  implemented in `cctb`.
