# Levels 3 and 4: Polarity and Anchor Resolution — Options

Companion to `ccdl-v3-draft.md`. Everything that document establishes is assumed here: the four
levels, group arrays, `anchorRef`, `anchorOccurrence`, `anchorPoint`, the evaluation model of §6 and
the translation obligations of §7. This file isolates one decision, sets out every option considered
for it, and records a verdict with its reasoning. Section references (§N) point into the main draft.

## The problem

Under `version: "2"` a group's `criteria` meant two different things depending on the side it was
written on. Level 3 was AND and level 4 OR in `inclusionCriteria`, and the reverse in
`exclusionCriteria`, so `[[A], [B]]` read as `A and B` on one side and `A or B` on the other, and
`[[A, B], [C]]` read as `(A and B) or C` under exclusion polarity.

For every rule in the language except one, that alternation is harmless, because those rules only ask
a group whether it matched. An anchor asks something harder. It has to hand back a *date*, and that
date comes from the resources that made the group match, so the rule that resolves it has to read the
group's clause structure rather than only its truth value. Under alternation, that structure means
two different things, so the anchor rule needs to know which polarity applies to the group in front
of it.

§6 only ever stated the AND form. An anchor defined in `exclusionCriteria` therefore had no stated
behaviour, even though §4 permits a reference from either side. `cctb` applied the AND form
everywhere and broke the exclusion side in both directions. For `[[A], [B]]`, meaning `A or B`, it
required an A date *and* a B date, so a patient with only A produced no anchor date and every
dependent silently dropped out. For `[[A, B]]`, meaning `A and B`, it took whichever date it found,
so a patient with only A produced an anchor date they should not have had. Neither case raised an
error. That silence is the property worth designing against.

## What is actually at stake

Two findings narrow the decision considerably, and both cut against the case the main draft currently
makes.

**The fork is one rule, not a second model.** Only step 3 of §6, witness selection, reads clause
structure. Step 5 distributes the window to every leaf criterion "regardless of whether it sits under
the AND or the OR branch," and step 6 runs the dependent group's normal level-3/4 logic, whatever
that is for its side. Both are already polarity-agnostic. Whatever is decided here, steps 4 through 6
are untouched.

**The OR form is a mirror, not a degenerate case.** Under exclusion polarity both inner levels flip,
so a witness is a tuple drawn from one existentially chosen clause: pick a clause, then take one
candidate per criterion in it, since level 4 is AND there. This is the reflection of the inclusion
rule rather than a simplification of it, and it is about one paragraph of specification.

**Compatibility is not a live benefit for any option.** `version: "3"` restructures `criteria` into
group objects, so no `version: "2"` document parses as v3 under any circumstances and a converter
runs on every document regardless. No option here can preserve v2 documents, only v2 *habits*.

**One capability is genuinely in play.** Alternation gives OR *inside* a group, so alternatives can
share one group's `relativeTimeRestrictions` and `anchorOccurrence`. Uniform AND cannot express that
except by distributing into conjunctive normal form or repeating the restriction across group arrays.

## Evaluation criteria

- **K1 — Locality.** Does editing one group change the dates another, untouched group receives?
- **K2 — Visibility.** Can a reader tell what a group's `criteria` mean from the group itself, or must
  they find where it is defined?
- **K3 — Enforceability.** Can the design's constraints be expressed in the JSON Schema, or must
  every builder enforce them?
- **K4 — Rule count.** How many forms does §6 step 3 need?
- **K5 — OR inside a group.** Are alternatives sharing one time restriction expressible directly?

K3 carries extra weight here. The defect being repaired was silent, so a design whose constraints can
only be enforced by convention reproduces the original failure mode at a different layer.

## The running example

Every option below renders the same query, so the JSON can be read side by side. `A` through `G`
stand for whole criterion objects, each with its own `context` and `termCodes`, elided because
nothing here depends on their contents.

> Include a patient who has (`A` or `B`) and `C`, and who has `D` within three days after that event.
> Exclude a patient for whom (`E` and `F`) holds, or for whom `G` holds.

The anchor is deliberately two-clause, so the tuple rule is visible, and the exclusion is deliberately
a compound reason of the shape `(E and F) or G`, because that is the shape whose encoding differs
between every option on the list.

---

## Option A — Uniform AND at levels 3 and 4

*The decision currently recorded in §1 and §3 of the draft.*

**Intent.** Remove polarity from the inner levels entirely, so a group's `criteria` mean one thing
wherever the group is written, and supply the OR that the exclusion side used to get from its outer
array at level 1 instead.

**Structure.** Level 3 is AND and level 4 is OR, on both sides, for every group. `[[A], [B]]` is
`A and B` everywhere. `A or B` is one group with `criteria` `[[A, B]]`. `(A and B) or C` is two group
arrays, the first holding a group with `[[A], [B]]` and the second a group with `[[C]]`. §6 step 3
states one witness rule, the tuple rule, and it applies to every anchor in the document.

**JSON.**

```json
{
  "version": "3",
  "inclusionCriteria": [                 /* level 1: OR of group arrays, both sides */
    [                                    /* level 2: AND of groups, both sides */
      {
        "id": "anc",
        "anchorOccurrence": "first",
        "criteria": [                    /* level 3: AND, both sides — every clause binds */
          [ A, B ],                      /* level 4: OR, both sides */
          [ C ]
        ]
      },
      {
        "id": "dep",
        "criteria": [ [ D ] ],
        "relativeTimeRestrictions": [
          { "anchorRef": "anc", "minOffset": "P0D", "maxOffset": "P3D" }
        ]
      }
    ]
  ],
  "exclusionCriteria": [                 /* level 1: OR — reads identically to inclusion */
    [                                    /* level 2: AND */
      { "criteria": [                    /* level 3: AND — E and F */
          [ E ],                         /* level 4: OR */
          [ F ]
        ] }
    ],
    [                                    /* the "or G" alternative, forced up to level 1 */
      { "criteria": [ [ G ] ] }
    ]
  ]
}
```

The exclusion costs two group arrays, because `E and F` and `G` are alternatives and level 1 is the
only OR available. `anc` resolves by the tuple rule: one candidate from `[A, B]`, one from `[C]`,
`maxOffset` measured from the earlier and `minOffset` from the later.

**Pros.**

- An anchor group means the same thing wherever it is defined, so `anchorRef` stays a plain global
  reference and cross-side references and §4's mandated anchor duplication are both safe.
- One witness rule. Every result §6 derives from it, the decomposition equivalence, the
  empty-candidate-set rule and the `"any"` product, has one form.
- Every constraint is structural. There is no rule a builder can violate while still emitting valid,
  meaningful JSON.
- Uniform with levels 1 and 2, which were already flattened to remove side-dependence when anchors
  were introduced.

**Cons.**

- Gives up OR inside a group. Alternatives that must share one `relativeTimeRestrictions` or
  `anchorOccurrence` have to be distributed into conjunctive normal form, which duplicates criteria
  multiplicatively and does not round trip through a builder.
- A list of compound disqualifying reasons becomes one group array per reason, which is more nesting
  than the v2 shape.
- Reinterprets every v2 exclusion side. Mitigated by the version break, since no v2 document parses
  as v3, but not by anything else if a document is hand-lifted into v3 shape.

---

## Option B — Alternation retained, both rules stated, relocation forbidden

**Intent.** Treat the defect as what it literally was, a missing paragraph in §6, and repair it by
writing the paragraph rather than by restructuring the language. Keep v2's inner polarity intact.

**Structure.** Levels 3 and 4 alternate by side as in v2. §6 step 3 states two witness rules. The
inclusion form is today's tuple rule, one candidate per clause. The exclusion form picks a clause
existentially, then takes one candidate per criterion within it, and induces the window from that
tuple's extremes exactly as the inclusion form does. Cross-side `anchorRef` stays legal, because an
anchor resolves by the polarity of its own definition site and the referencing group is unaffected. A
new validation rule forbids relocating a group between sides, and forbids §4's anchor duplication
from crossing sides, so that definition site can never change under an existing reference.

**JSON.**

```json
{
  "version": "3",
  "inclusionCriteria": [                 /* level 1: OR of group arrays, both sides */
    [                                    /* level 2: AND of groups, both sides */
      {
        "id": "anc",
        "anchorOccurrence": "first",
        "criteria": [                    /* level 3: AND on THIS side */
          [ A, B ],                      /* level 4: OR on THIS side */
          [ C ]
        ]
      },
      {
        "id": "dep",
        "criteria": [ [ D ] ],
        "relativeTimeRestrictions": [
          { "anchorRef": "anc", "minOffset": "P0D", "maxOffset": "P3D" }
        ]
      }
    ]
  ],
  "exclusionCriteria": [                 /* level 1: OR — unchanged, uniform on both sides */
    [                                    /* level 2: AND — unchanged, uniform on both sides */
      { "criteria": [                    /* level 3: OR on THIS side — (E and F) or G */
          [ E, F ],                      /* level 4: AND on THIS side */
          [ G ]
        ] }
    ]
  ]
}
```

The inclusion side is byte-identical to Option A. The whole difference is the exclusion side, which
collapses to one group array holding one group, because `[[E, F], [G]]` reads as `(E and F) or G`
under exclusion polarity. That compression is what B buys and it is the same JSON a v2 author would
have written.

The crux case is an anchor on the exclusion side, which B is the only option that has to specify:

```json
"exclusionCriteria": [
  [
    {
      "id": "xanc",
      "anchorOccurrence": "first",
      "criteria": [                      /* level 3: OR — the witness comes from ONE chosen clause */
        [ E, F ],                        /* level 4: AND — choosing this clause needs an E and an F */
        [ G ]                            /* choosing this one needs a single G */
      ]
    }
  ]
]
```

`xanc` resolves by the exclusion witness rule: choose a clause existentially, then take one candidate
per criterion in it, so either an `E` and an `F` together, or a single `G`. The identical `criteria`
array under `inclusionCriteria` would instead demand one candidate from `[E, F]` and one from `[G]`,
which is a different patient set and a different date. Moving that group between the two arrays is
what the validation rule has to forbid.

**Pros.**

- Coherent. With the relocation ban in place there is no combination of legal edits that silently
  rewindows a dependent, and steps 4 through 6 need no changes at all.
- Smallest specification delta of any option that keeps alternation. One extra paragraph in §6 step 3.
- Preserves OR inside a group on the exclusion side, so compound disqualifying reasons keep their v2
  shape and alternatives there can share one group's time restriction.
- Authors carrying v2 habits are not retrained.

**Cons.**

- **Fails K3.** The relocation ban cannot be expressed in the schema, because the JSON is structurally
  valid with the group on either side. It lives in every builder that offers an inclusion/exclusion
  toggle, and a builder that gets it wrong emits a valid document with silently different windows,
  which is the same failure mode as the `cctb` defect one layer up.
- **Fails K1.** The non-local effect still exists. It is banned rather than removed.
- **Fails K2.** A reader cannot tell what `[[A], [B]]` means without finding where the group is
  defined, and the reference site gives no hint.
- Two witness rules to state, implement, and test.
- Without the relocation ban the option is not merely worse but inconsistent, since §4 mandates
  duplicating an anchor across group arrays and those arrays can sit on different sides. The ban is
  not optional polish.

---

## Option C — Explicit clause operator on every group

**Intent.** Keep both operators available, but key them to something visible in the group rather than
to the group's location, so the anchor rule reads a field instead of an address.

**Structure.** Every group carries an operator field, `"and"` or `"or"`, naming how its clause list at
level 3 combines, with level 4 always taking the dual. The side a group is written on determines only
whether it includes or excludes. §6 step 3 states two witness rules and selects between them by
reading the field.

**JSON.**

```json
{
  "version": "3",
  "inclusionCriteria": [                 /* level 1: OR of group arrays, both sides */
    [                                    /* level 2: AND of groups, both sides */
      {
        "id": "anc",
        "clauseOperator": "and",         /* names level 3; level 4 takes the dual */
        "anchorOccurrence": "first",
        "criteria": [                    /* level 3: AND, per the field above */
          [ A, B ],                      /* level 4: OR, the dual */
          [ C ]
        ]
      },
      {
        "id": "dep",
        "clauseOperator": "and",
        "criteria": [ [ D ] ],
        "relativeTimeRestrictions": [
          { "anchorRef": "anc", "minOffset": "P0D", "maxOffset": "P3D" }
        ]
      }
    ]
  ],
  "exclusionCriteria": [                 /* level 1: OR */
    [                                    /* level 2: AND */
      {
        "clauseOperator": "or",          /* names level 3; level 4 takes the dual */
        "criteria": [                    /* level 3: OR, per the field — (E and F) or G */
          [ E, F ],                      /* level 4: AND, the dual */
          [ G ]
        ]
      }
    ]
  ]
}
```

Structurally identical to B, with the polarity now stated rather than inferred from the enclosing key.
Because it is stated, the exclusion group can be moved, copied to the inclusion side, or referenced
from anywhere without its meaning changing, and the reverse shape is equally available: an inclusion
group may carry `"clauseOperator": "or"` to express `(A and B) or C` as a positive requirement, which
is the K5 capability neither A nor B offers. The cost is visible in the listing. Every group now
carries the field, and `"criteria": [[E, F], [G]]` can no longer be read without it.

**Pros.**

- Passes K1 and K2 outright. The operator travels with the group, so relocation, duplication and
  cross-side reference are all safe, and the meaning is legible at the group itself.
- Passes K3. Nothing needs enforcing by convention, because there is no address-derived behaviour to
  protect.
- The only option that delivers K5 symmetrically. Alternatives sharing one `relativeTimeRestrictions`
  are expressible on the inclusion side too, which neither A nor B offers.

**Cons.**

- A branch in every rule that reads clause structure, not only the anchor rule.
- A decision every builder must make on every group, and a field every reader must check before the
  criteria can be read at all. Two documents with identical `criteria` can now mean different things,
  which is the problem A removes.
- Two witness rules, as in B.
- The capability it buys is, on current evidence, rarely needed. The draft's own migration guidance
  describes CNF distribution as "occasionally what you want."

---

## Option D — Operator declared only on groups used as anchors

**Intent.** Pay C's cost only where the problem exists. `anchorOccurrence` and `anchorPoint` are
already required only on groups that something references, so extend that pattern to the operator.

**Structure.** A group referenced by `anchorRef` declares its clause operator. Unreferenced groups
follow their side's polarity.

**JSON.**

```json
"exclusionCriteria": [
  [                                      /* level 2: AND of groups */
    {
      "id": "xanc",                      /* referenced by an anchorRef somewhere else */
      "anchorClauseOperator": "and",     /* declared: level 3 AND, level 4 OR */
      "anchorOccurrence": "first",
      "criteria": [ [ E, F ], [ G ] ]    /* so this reads (E or F) and G */
    },
    {
                                         /* no field, so side polarity applies: */
                                         /* level 3 OR, level 4 AND */
      "criteria": [ [ E, F ], [ G ] ]    /* so this reads (E and F) or G */
    }
  ]
]
```

The two groups in that array carry identical `criteria` and differ only in that something, elsewhere
in the document, names the first one. The listing shows the defect directly. Either
`anchorClauseOperator` governs the date alone, in which case `xanc` is true when `G` alone holds but
its date demands an `E` and an `F`, or it governs truth as well, in which case the second group means
`(E and F) or G` and the first means `(E or F) and G`, and deleting the `anchorRef` that points at it
silently converts the first into the second.

**Pros.**

- Cheaper than C. Most groups carry no new field.
- Follows an established precedent in §4 for reference-triggered required fields.

**Cons.**

- Does not survive analysis. The declared operator must govern either the date alone or the truth as
  well, and both branches fail:
  - **Date only.** The group's truth follows side polarity while its date follows the declaration, so
    an exclusion group `[[A], [B]]` true via A alone, declared an AND anchor, either matches with no
    available date or takes a date from resources that played no part in its match. §6's premise is
    that the date comes from the resources that made the group match. Decoupling them breaks that
    premise silently.
  - **Truth as well.** A group's boolean meaning now depends on whether some other group elsewhere in
    the document names it in an `anchorRef`. Adding the reference changes the clause semantics,
    removing the last one changes them back.
- The precedent it leans on does not hold. `anchorOccurrence` and `anchorPoint` select among the
  resources that already made the group match and never change whether it matched. A clause operator
  is a different class of field.
- Avoiding both branches means declaring the operator on every group, which is Option C.

---

## Option E — Fold inclusion and exclusion into every group

**Intent.** Remove the top-level side split. Give each group both an inclusion block and an exclusion
block, so polarity is carried by a block name rather than by a document address.

**Structure.** The top-level `inclusionCriteria`/`exclusionCriteria` pair disappears. A group becomes
roughly `{id, inclusion: [[...]], exclusion: [[...]], ...}`, the inclusion block read AND-of-OR and the
exclusion block read OR-of-AND, and the group matches when its inclusion block matches and its
exclusion block does not.

**JSON.**

```json
{
  "version": "3",
  "criteria": [                          /* level 1: OR of group arrays */
    [                                    /* level 2: AND of groups */
      {
        "id": "anc",
        "anchorOccurrence": "first",
        "inclusion": [                   /* level 3: AND — the key sets the polarity */
          [ A, B ],                      /* level 4: OR */
          [ C ]
        ]
      },
      {
        "id": "dep",
        "inclusion": [ [ D ] ],
        "relativeTimeRestrictions": [
          { "anchorRef": "anc", "minOffset": "P0D", "maxOffset": "P3D" }
        ]
      },
      {
        "exclusion": [                   /* level 3: OR — the key sets the polarity */
          [ E, F ],                      /* level 4: AND */
          [ G ]
        ]                                /* group matches when this block does NOT */
      }
    ]
  ]
}
```

One root, no side keys. The exclusion becomes an ordinary member of the group array and keeps its v2
shape, and `anc` can only resolve against an `inclusion` block, so no witness rule has to ask which
polarity applies. A group may carry both keys at once, `{"inclusion": [[A]], "exclusion": [[E]]}`
meaning `A` present and `E` absent.

C1 is visible as soon as a second level-1 alternative exists. The exclusion is global, but nothing
about one group array constrains another, so it has to be repeated in full:

```json
"criteria": [                                           /* level 1: OR of group arrays */
  [                                                     /* level 2: AND */
    { "id": "anc", "inclusion": [ [ A, B ], [ C ] ] },
    { "...": "dep" },
    { "exclusion": [ [ E, F ], [ G ] ] }                /* level 3 OR, level 4 AND */
  ],
  [                                                     /* the OR alternative */
    { "id": "alt", "inclusion": [ [ H ] ] },
    { "exclusion": [ [ E, F ], [ G ] ] }                /* repeated verbatim: level 1 is an OR, */
  ]                                                     /* so the other array's copy does not bind here */
]
```

**Pros.**

- **Dissolves the question rather than answering it.** The resources that make a group match are always
  its inclusion block's resources, because an exclusion block asserts absence and absence has no date.
  An anchor can therefore only ever resolve against an inclusion block, AND-of-OR, everywhere. There is
  no exclusion-side anchor to specify, by construction rather than by decree.
- Passes K1, K2 and K3. Polarity is a local, visible property and there is nothing to forbid.
- Preserves v2's inner shapes for both blocks, so v2 authoring habits transfer unchanged.

**Cons.**

- **Global exclusions lose their home.** Real exclusion criteria are cohort-wide rather than per-group.
  Because level 1 is an OR, an exclusion sitting in one alternative does not constrain the others, so
  every global exclusion must be replicated into every group array that could admit a patient. Keeping
  a top-level exclusion block alongside the per-group ones avoids the replication but puts exclusions
  in two places, which is the problem the fold was meant to remove.
- Each block needs its own `relativeTimeRestrictions`, since "exclude if E occurred within 30 days of
  anchor X" is an ordinary requirement. That is a second attachment point for §4's machinery and a
  second place for §6 to apply it.
- The largest break of any option. Per-group negation is a different language rather than a repair to
  this one, and every document, builder and translator changes shape. Expressiveness survives by De
  Morgan, but nothing else does.
- Does not deliver K5 for inclusion. OR inside a group remains unavailable for positive requirements.

---

## Comparison

| | K1 Locality | K2 Visibility | K3 Enforceable | K4 Rules | K5 OR in group |
| --- | --- | --- | --- | --- | --- |
| **A** Uniform AND | yes | yes | yes | 1 | no |
| **B** Alternation + ban | banned, not removed | no | no | 2 | exclusion only |
| **C** Operator per group | yes | yes | yes | 2 | both sides |
| **D** Operator on anchors | — | — | — | — | — |
| **E** Folded groups | yes | yes | yes | 1 | no |

D is struck rather than scored. It collapses into C or into incoherence.

A, C and E all pass K1 through K3. The decision among them is K4 against K5 against the size of the
break. B is the only option that fails K3, and E is the only one that changes the shape of every
document.

## Verdict

**Adopt Option A.** Two reasons, in increasing order of weight.

**The capability A gives up is rarely needed and has a workaround.** K5 is the one real thing on the
table, and the draft's own migration guidance describes the case as occasional. Where it does arise,
repeating the `relativeTimeRestrictions` entry across group arrays expresses it, at a verbosity cost
paid by a generator rather than by a person.

**B fails on the criterion that matters most here.** Its relocation ban is correct and sufficient, and
the draft currently understates how cheap the rest of B is. But the ban cannot be expressed in the
schema, so it is enforced by convention in every builder, and a builder that violates it emits a valid
document whose windows are quietly wrong. That is the same class of failure as the defect this
decision exists to repair, relocated from the translator to the builder. A design that answers a silent
failure with a rule that can be silently broken has not finished the job. A removes the hazard instead
of prohibiting it.

E deserves the closest look of the alternatives, and it handles the anchor question better than any
other option by making it unaskable. It is rejected on the replication of global exclusions across
alternatives, which is a structural cost paid on every real cohort definition, against an anchor
benefit that A obtains for free.

## What would reverse this

A single trigger, and it is C rather than B or E that would win. If authors turn out to need OR inside
a group routinely rather than occasionally, specifically alternatives that must share one group's
`relativeTimeRestrictions` or `anchorOccurrence`, then CNF distribution stops being an acceptable
workaround and the explicit per-group operator earns its cost. That is a question about observed
authoring patterns, and the evidence for it does not exist yet. Nothing about adopting A now forecloses
adding the field later, since a group with no operator field would default to AND and every existing
document would keep its meaning.
