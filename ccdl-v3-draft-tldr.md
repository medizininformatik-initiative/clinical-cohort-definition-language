# Relative Time Constraints — Spec Summary (TL;DR)

> Matter-of-fact version of [ccdl-v3-draft.md](ccdl-v3-draft.md) — the rules, not the reasoning. Read
> that document for rationale, rejected alternatives, and worked-example walkthroughs; this one is a
> compact reference for what the schema and behavior actually are. `version: "3"`, draft, not adopted.
> Translation targets: CQL and Delta Lake SQL. Not FHIR Search.

## Structure: four fixed levels

| Level | What | Inclusion | Exclusion |
|---|---|---|---|
| 1 | `inclusionCriteria`/`exclusionCriteria` — array of group arrays | OR | OR |
| 2 | A group array — array of `Group` objects | AND | AND |
| 3 | A group's `criteria`, outer array | AND | OR |
| 4 | A group's `criteria`, inner array | OR | AND |

No metadata (`id`, `relativeTimeRestrictions`, `anchorOccurrence`, `anchorPoint`) outside level 2. Not
recursive: a group array can't contain another group array, `criteria` can't contain another group.
`criteria` and the level-1/2 arrays are always the full nested shape, never flattened for a single
element.

```json
{
  "inclusionCriteria": [
    [
      {
        "id": "group-name",
        "relativeTimeRestrictions": [ { "anchorRef": "...", "minOffset": "-P3D", "maxOffset": "P0D" } ],
        "anchorOccurrence": "first",
        "anchorPoint": "start",
        "criteria": [ [ /* level 4 */ ], [ /* level 3 clause */ ] ]
      }
    ]
  ]
}
```

## Group fields

- `id` — required only if referenced as an anchor elsewhere.
- `criteria` — unchanged two-level CNF/DNF shape.
- `relativeTimeRestrictions` — array, see below; omit if the group has no time constraint.
- `anchorOccurrence: "first" | "last" | "any"` — required if this group is used as an anchor (not
  for `now`). Selects which candidates may serve as the witness: earliest only, latest only, or all
  of them. `"any"` is not implemented in `cctb` yet.
- `anchorPoint: "start" | "end"` — optional, default `"start"`; only matters for `Period`-valued matches.

## `relativeTimeRestrictions`

Array of:

```json
{ "anchorRef": "<group id>", "minOffset": "-P3D", "maxOffset": "P0D" }
```

- `anchorRef` — id of the anchor group. Resolution is global (any group in the document, either side).
- `minOffset`/`maxOffset` — signed ISO 8601 duration, negative = before anchor, positive = after. At
  least one required per entry; omitting one leaves that side unbounded.
- **Multiple entries → AND-intersected window, single shared matching resource:** `windowStart =
  Max` of every entry's own start, `windowEnd = Min` of every entry's own end. Distinct from
  duplicating the group across two separate groups (independent existence checks vs. one resource
  satisfying both windows at once).

## Requiredness

A group's own truth is required by every group array it is a **member** of. `anchorRef` resolution is
independent of membership — referencing an anchor from a group array that doesn't list it contributes
only the anchor's resolved *date*, never its own truth. An anchor needed, non-required, by more than
one group array must be duplicated (separate `id` per copy) — and `id` is what carries event
identity: same id = same event, different ids = different events, in all three `anchorOccurrence`
modes. This holds across sides: an anchor defined in `inclusionCriteria` may be referenced from
`exclusionCriteria` and the reverse, and requiredness still follows membership only — the reference
takes the date, never the anchor's own truth.

## `anchorOccurrence: "any"` — one shared witness per group array

`"any"` is the mode that leaves the candidate set whole. `"first"`/`"last"` narrow it to one
element, fixing the witness before any dependent is evaluated, so every reference trivially agrees.
`"any"` defers the choice to the rest of the query, which makes it the only mode in which two
references to one anchor could, in principle, disagree about which occurrence they mean — hence the
scope rule.

**Scope rule — this is the whole semantics.** Within one group array, every
`relativeTimeRestrictions` entry naming the same `anchorRef` is satisfied by the **same** anchor
instance: `∃a: φ_B(a) ∧ φ_C(a)`, not `(∃a: φ_B(a)) ∧ (∃a: φ_C(a))`. One `anchorRef`, one event — in
all three occurrence modes. Group arrays are independent OR-alternatives, so references from two
different arrays never coordinate on a witness.

- **Use case:** chains longer than one hop. E.g. delirium within 30 days of a diagnosis,
  antipsychotic within 3 days of *that specific* delirium episode — with `"first"`/`"last"` on
  `delirium`, no single choice of occurrence is correct for every patient. With a single referencing
  group, shared and independent readings coincide anyway.
- **Independent witnesses, when that's what's meant:** duplicate the anchor — identical `criteria`,
  two `id`s, one dependent pointing at each. §4's rule unchanged: different ids = different events,
  same id = same event. Shared is the strictly stronger reading, so duplication recovers
  independence while nothing recovers sharing from independence — hence shared is the default.
  Corollary for tooling: never auto-merge two identical anchor definitions that are referenced with
  `"any"` (safe for `"first"`/`"last"`, meaning-changing here).
- **Multi-clause anchors:** defined, not restricted. The witness is a tuple, one candidate per
  clause, and the window comes from its extremes (`maxOffset` from the earliest, `minOffset` from
  the latest) — the same asymmetric rule `"first"`/`"last"` already use.
- **No null-guard:** an empty candidate set already makes the existential false, and `"any"` is
  never hoisted to a scalar date, so the translation obligations below have nothing to guard. That
  section states it as a MUST NOT.
- **Translation:** one correlated `exists ... such that ...` (CQL) / correlated join (SQL) per
  anchor per group array, wrapping a conjunction of the window tests from *every* referencing group
  in that array — not one existential per reference site, and not a hoisted per-patient anchor date.
  This couples sibling groups: a group with an `"any"` entry cannot be translated in isolation.

## `now` criterion

```json
{ "type": "now" }
```

Resolves to the evaluation timestamp, matches every patient trivially, has no `context`/`termCodes`.
Used only to be referenced via `anchorRef`.

## Interaction with absolute `timeRestriction`

A criterion's own `timeRestriction` and any inherited `relativeTimeRestrictions` window intersect
(AND) — same as any two independent filters on one criterion.

## Evaluation algorithm

Existential: the group matches when **every `relativeTimeRestrictions` entry has a witness** — an
anchor occurrence from that entry's anchor group's own matches — such that the group's criteria match
inside the intersection of the windows those witnesses induce. One witness per entry, so the common
single-entry case has exactly one. The witnesses sit on the anchor side; the single shared matching
resource of "multiple entries" above sits on the dependent side. `anchorOccurrence` only filters
which candidates are eligible to be an entry's witness (earliest / latest / all), so
`"first"`/`"last"` are one-element projections of the same rule, not separate mechanisms. They are
not merely a convenience over `"any"`: `"first"` means the earliest occurrence specifically, which is
a different constraint, not a shorthand. This is presentation, not a default change —
`anchorOccurrence` stays required, and translators should still hoist `"first"`/`"last"` to one
scalar date.

Per `relativeTimeRestrictions` entry (potentially a different anchor group each time):

1. **Gather candidates** — every resource matching the anchor group's own `criteria`. If that group
   is itself windowed, its own window is already applied (see "Chaining").
2. **Reduce to a point** — `dateTime` as-is; `Period` reduced via `anchorPoint` (default `start`).
3. **Select the eligible witnesses** — earliest only (`"first"`), latest only (`"last"`), or all
   (`"any"`).
   - If the anchor group's level 3 is AND (multiple required clauses), a witness is a **tuple**, one
     candidate per clause, and the window comes from its extremes: `maxOffset` from the earliest
     member, `minOffset` from the latest. Under `"first"`/`"last"` each clause contributes one
     candidate, so the product is a single tuple and this is today's behavior. Single-clause:
     earliest == latest, no change.
   - **Empty candidate set ⇒ no witness ⇒ the group does not match this patient.** This is what an
     existential over an empty set means, not a separate rule, so it holds for every mode, every
     entry (any one empty entry is enough) and every clause. Not configurable, not a schema field.

Then, once per group (after intersecting every entry's bounds — see "multiple entries" above):

4. **Compute the bound** per entry, intersect across entries (`Max` of starts, `Min` of ends).
5. **Distribute** `[windowStart, windowEnd]` to every leaf criterion in the group's `criteria` tree,
   using the existing `timeRestriction`/overlap-sufficiency mechanism.
6. **Evaluate** the group's normal AND/OR logic over the now-filtered candidates.

### Chaining

A chained group's candidates are the matches it **qualifies** on, meaning its own window is already
applied. A resource matching its criteria but outside its own window cannot date anything
downstream. A criterion's own absolute `timeRestriction` counts as part of matching, so an anchor
group can be date-bounded in its own right. Under `"any"` the quantifiers nest rather than interact:
a downstream `"any"` reference quantifies over the intermediate group's already-window-filtered
matches, and each anchor id is shared per group array independently of the others.

**`cctb` does not do this** — `resolveAnchorDates` gathers raw criteria matches, only
`combineCriteria` applies the window — so a non-qualifying occurrence can date a downstream window.
A conformance defect against the semantics, not a missing feature.

## Translation obligations (not semantics)

Nothing here is observable in a CCDL document. It exists because translators hoist `"first"`/`"last"`
to one scalar date, which discards the empty-candidate-set case.

A hoisting translator **MUST NOT** rely on the target engine's own null propagation to make an
undefined anchor produce no-match. That propagation is not guaranteed, and Blaze 0.34 silently treats
the window as unbounded instead, which is silent wrong inclusion rather than an error. A translator
**MUST** emit an explicit guard ("anchor date is not null") alongside the window test, with the guard
being the conjunction of every entry's own check, and **MUST** verify this against a real instance of
the target engine. An `"any"` reference is never hoisted, so a translator **MUST NOT** emit a
date-null guard for one.

See [ccdl-v3-draft.md § 7](ccdl-v3-draft.md) for the engine-level evidence behind these obligations
and for how `cctb` implements them.

## Compatibility

Breaking change from `version: "2"`. `version: "3"` = everything above, all at once, not staged. Not
published or adopted yet.

## Examples

Eight worked examples in [example-json/ccdl-v3/](example-json/ccdl-v3/), with a reading guide in
[example-json/ccdl-v3/README.md](example-json/ccdl-v3/README.md) and per-file notes in
[ccdl-v3-draft.md § Worked examples](ccdl-v3-draft.md#worked-examples). Five translate through
`cctb`; the three `anchorOccurrence: "any"` examples do not, by design.
`ccdl-example-all-features-draft.json` exercises every feature at once.

## Open questions

- `anchorOccurrence: "any"` implementation in `cctb` — semantics are settled (above), the
  translator work is not done yet. Two known costs: sibling groups' translation is coupled, and
  multi-clause `"any"` quantifies over a product of candidate sets, so single-clause is the sensible
  first increment.
- Chained anchors in `cctb` do not apply the chained group's own window when gathering candidates —
  settled semantics, open implementation gap, changes results rather than only performance.
- Overlap vs. containment for narrow relative windows — step 5's inherited overlap-sufficiency rule
  may be too lenient at 72h-scale windows. Not yet decided.
