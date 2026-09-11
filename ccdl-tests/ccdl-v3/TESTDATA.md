# Test data, drawn

`README.md` says what each dataset contains. This file draws it, because these datasets are about
*when* things happened relative to each other, and a list of dates is a poor way to see that.

Start here if you are implementing a translator and want to know what a test is actually asking of
you, or if a test is failing and you want to see which patient you got wrong.

## Reading the diagrams

```
◇              an anchor resource — the event a window is measured from
◆              a candidate witness — an anchor with `anchorOccurrence: "any"`, where the
               query tries each occurrence in turn instead of fixing on one
●              a criterion resource — the thing the query is looking for
▣              a resource matched through something other than a date, e.g. a reference
▓              the window — where a matching resource has to fall
end◄──►start   an inverted window: it has no width, so nothing can fall inside it
✓ / ✗          whether the patient ends up selected
```

Each patient is a swimlane: the patient and its result, the resources it has, then the window or
windows those resources produce. Three columns — labels on the left, the timeline in the middle, the
outcome on the right. Time runs left to right and each chart is scaled to its own date range, so
compare positions within a chart rather than between charts.

Windows are drawn per patient, not per query, because they are computed from that patient's own data.
Two patients running the same query can end up with completely different windows, and some with none
at all. Where an anchor is `"any"` there is a window per candidate witness, since the query tries each
in turn and needs only one to work.

## `ccdl-example-hemoglobin-between-two-anchors`

A haemoglobin measured between the diverticular disease diagnosis and the resection.

The group carries two `relativeTimeRestrictions` entries, each bounded on one side only, and they
intersect:

```
entry 1   anchorRef: anchor-colon-diverticular-disease   minOffset: P0D    → window starts at the diagnosis
entry 2   anchorRef: anchor-colon-resection              maxOffset: P0D    → window ends at the resection
```

So `windowStart` comes from one anchor and `windowEnd` from the other, and a single haemoglobin has
to fall inside both.

```
                              │   Jan 10  Jan 20           Feb 10          Mar 1           │ result
                              │   |       |                |               |               │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = between             │                                                            │ ✓ selected
  resources                   │   ◇K57.3  ●Hb              ◇5-455.3                        │
  window                      │   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                               │ Hb falls inside
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = after-op            │                                                            │ ✗ not selected
  resources                   │   ◇K57.3                   ◇5-455.3        ●Hb             │
  window                      │   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                               │ Hb is past the end
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = inverted            │                                                            │ ✗ not selected
  resources                   │   ◇5-455.3●Hb              ◇K57.3                          │
  window                      │   end◄─────────────────────►start                          │ empty, start after end
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

`expected.json` therefore names `between` alone:

```json
{ "includedPatients": ["between"], "excludedPatients": ["after-op", "inverted"] }
```

### What each patient is for

**`between`** is the positive control. Nothing subtle: both anchors resolve, the haemoglobin sits
between them.

**`after-op`** has exactly the same anchors and a haemoglobin ten days too late. It catches an
implementation that resolves the window but never applies it, or that applies only the first of the
two entries — note that its haemoglobin *does* satisfy entry 1 on its own, since that entry has no
upper bound. Only the intersection excludes it.

**`inverted`** is the one worth dwelling on. Its resection came *before* its diagnosis, so
`windowStart` lands after `windowEnd` and the window is empty. No resource can satisfy it, so the
patient is not selected — and that is all that should happen. An implementation that hands an
inverted interval straight to its query engine may get an error rather than an empty result, which
fails the whole evaluation and takes every other patient down with it. This is not hypothetical: the
CQL reference implementation does exactly that, and needs the emptiness made explicit before the
membership test runs.

## `ccdl-example-hemoglobin-last-24h`

The minimal anchored query, and the only one whose window moves: its anchor is the `now` criterion,
so the dataset's dates are relative to `referenceDate` and a harness has to shift them.

The window is a *day* wide, not 24 clock hours. Every criterion date is compared at day precision, so
`minOffset: -PT24H` reaches back to yesterday's date and no further.

```
                              │          now−3              now−1    now                   │ result
                              │          |                  |        |                     │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = recent              │                                                            │ ✓ selected
  resources                   │                                      ●Hb                   │
  window                      │                             ▓▓▓▓▓▓▓▓▓▓                     │ Hb is today
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = stale               │                                                            │ ✗ not selected
  resources                   │          ●Hb                                               │
  window                      │                             ▓▓▓▓▓▓▓▓▓▓                     │ Hb is two days too early
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = none                │                                                            │ ✗ not selected
  resources                   │                                                            │ no haemoglobin at all
  window                      │                             ▓▓▓▓▓▓▓▓▓▓                     │ nothing to fall inside it
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

## `ccdl-example-or-scoped-anchors-draft`

Three group arrays OR'd, so a patient needs only one of them. Array 3 references array 2's anchor
without listing it: it needs the diagnosis to measure from, not as a criterion of its own.

```
                              │     Jan 5      Jan 10 Jan 13         Jan 20                │ result
                              │     |          |      |              |                     │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = gender-crp          │                                                            │ ✓ selected
  resources                   │     ●CRP, female                                           │
  window                      │                                                            │ array 1 has no window
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = donepezil           │                                                            │ ✓ selected
  resources                   │                ◇F00                  ●N06DA02              │
  window                      │                ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓            │ array 2: 30 days after the dx
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = weight              │                                                            │ ✓ selected
  resources                   │                ◇G30   ●Weight                              │
  window                      │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓            │ array 3: dx−7d onward, open ended
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = none                │                                                            │ ✗ not selected
  resources                   │     ●CRP, male                                             │
  window                      │                                                            │ 1 needs female, 2 and 3 need a dx
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

## `ccdl-example-hemoglobin-after-procedure`

A multi-clause AND-anchor. The two OPS codes are separate clauses, so the anchor resolves to *two*
dates: the window runs from the later one minus 24h to the earlier one plus 24h. Same-day clauses
give a ±1 day window; clauses that drift apart shrink it and eventually invert it.

Patients sit in different months, so lanes are drawn relative to each patient's own procedure.

```
                              │      −1d  proc +1d             +4d                         │ result
                              │      |    |    |               |                           │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = first-path          │                                                            │ ✓ selected
  resources                   │           ◇5-470.1                                         │
                              │           ◇8-718.94                                        │
                              │           ●Hb                                              │
                              │           ●E10.9                                           │
  window                      │      ▓▓▓▓▓▓▓▓▓▓▓                                           │ both clauses same day: ±1 day
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = second-path         │                                                            │ ✓ selected
  resources                   │           ◇5-470.1                                         │
                              │           ◇8-718.94                                        │
                              │           ●Hb                                              │
                              │           ●E11.9                                           │
  window                      │      ▓▓▓▓▓▓▓▓▓▓▓                                           │ qualifies via the second array
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = spread-out          │                                                            │ ✗ not selected
  resources                   │      ◇5-470.1  ●Hb             ◇8-718.94                   │
                              │                ●E10.9                                      │
  window                      │           end◄────────────►start                           │ latest−24h is after earliest+24h
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = no-procedure        │                                                            │ ✗ not selected
  resources                   │                ●Hb                                         │
                              │                ●E10.9                                      │
  window                      │                                                            │ no anchor clause resolves
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

## `ccdl-example-any-chained-anchors-draft`

The shared-witness rule. `group-delirium-after-diagnosis` carries `anchorOccurrence: "any"`, and two
groups reference it — haloperidol within 3 days after, sodium within a day either side. Because both
name the *same* anchor inside the *same* group array, one single episode has to satisfy both.

`◆` marks a candidate witness. A window is drawn per candidate, because `any` means the query tries
each one in turn and needs only one to work.

```
                              │     dx     Jan 5      Jan 11           Jan 20              │ result
                              │     |      |          |                |                   │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = same-episode        │                                                            │ ✓ selected
  resources                   │     ◇F00              ◆F05                                 │
                              │                       ●Na                                  │
                              │                         ●Halo                              │
  F05 candidates              │     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓            │ delirium must be within 30d of dx
  ⤷ try Jan 11                │                     ▓▓▓▓▓▓▓▓▓                              │ Halo ✓ and Na ✓ — one episode, both
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = split               │                                                            │ ✗ not selected
  resources                   │     ◇F00   ◆F05                        ◆F05                │
                              │              ●Halo                     ●Na                 │
  ⤷ try Jan 5                 │            ▓▓▓▓▓▓▓                                         │ Halo ✓, but no Na within ±1d
  ⤷ try Jan 20                │                                      ▓▓▓▓▓▓▓▓              │ Na ✓, but no Halo within +3d
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = no-delirium         │                                                            │ ✗ not selected
  resources                   │     ◇F00              ●Na                                  │
                              │                         ●Halo                              │
  candidates                  │                                                            │ no F05 at all, so no witness to try
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

## `ccdl-example-any-chain-three-hops-draft`

`any` anchors stacked three deep. Each hop's window starts where the hop above it landed, so the
query is one nested existential rather than three independent checks sharing names.

Each patient gets its own chart here, because the interesting relationships are inside a patient and
the dates span months.

```
                              │      Jan 1    Jan 4             Jan 11                     │ result
                              │      |        |                 |                          │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = chain               │                                                            │ ✓ selected
  resources                   │      ◆A41.5   ◆N17.0            ◆8-85a.0                   │
                              │                                 ●Hb                        │
  ⤷ sepsis Jan 1              │      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                                  │ AKI must land within 7d
  ⤷ AKI Jan 4                 │               ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓       │ dialysis within 14d
  ⤷ dialysis Jan 11           │                                 ▓▓▓▓                       │ Hb within 1d ✓
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

```
                              │   Jan 1                              Mar 1 Mar 10          │ result
                              │   |                                  |     |               │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = late-episode        │                                                            │ ✓ selected
  resources                   │   ◆A41.5                             ◆A41.5◆8-85a.0        │
                              │                                        ◆N17.0              │
                              │                                            ●Hb             │
  ⤷ try sepsis Jan 1          │   ▓▓▓▓▓                                                    │ no AKI in range — try the next
  ⤷ try sepsis Mar 1          │                                      ▓▓▓▓▓                 │ AKI Mar 4 ✓
  ⤷ AKI Mar 4                 │                                        ▓▓▓▓▓▓▓▓            │ dialysis Mar 10 ✓, then Hb ✓
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

```
                              │    Jan 1                              Feb 15               │ result
                              │    |                                  |                    │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = broken-link         │                                                            │ ✗ not selected
  resources                   │    ◆A41.5                             ◆N17.0               │
                              │                                           ◆8-85a.0         │
                              │                                           ●Hb              │
  ⤷ sepsis Jan 1              │    ▓▓▓▓▓▓▓                                                 │ the only sepsis; AKI is six weeks later
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

```
                              │      Jan 1    Jan 4             Jan 11                     │ result
                              │      |        |                 |                          │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = no-hemoglobin       │                                                            │ ✗ not selected
  resources                   │      ◆A41.5   ◆N17.0            ◆8-85a.0                   │
  ⤷ dialysis Jan 11           │                                 ▓▓▓▓                       │ chain holds, but there is no Hb
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

## `ccdl-example-any-multi-clause-anchor-draft`

A multi-clause `any` anchor: the witness is a **tuple**, one sepsis and one kidney injury, drawn from
the product of the two clauses' candidates. The window runs from the later tuple member to the earlier
member plus the offset, so a tuple whose members are far apart produces no window at all.

```
                              │         Jan 1  Jan 2   Jan 3                               │ result
                              │         |      |       |                                   │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = tight               │                                                            │ ✓ selected
  resources                   │         ◆A41.5 ◆N17.0  ●Hb                                 │
                              │                ●CRP                                        │
  ⤷ tuple Jan 1 + Jan 2       │                ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                           │ Hb window: latest → earliest+3d
  ⤷ same tuple, CRP           │                ▓                                           │ CRP window: latest → earliest+1d
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

```
                              │               Feb 20   Feb 22                              │ result
                              │               |        |                                   │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = two-options         │                                                            │ ✓ selected
  resources                   │               ◆A41.5   ●Hb                                 │ (a Jan 1 sepsis also exists, off-chart)
                              │                   ◆N17.0                                   │
                              │                   ●CRP                                     │
  ⤷ tuple Feb 20 + Feb 21     │                   ▓▓▓▓▓▓▓▓▓▓▓                              │ the Jan 1 pairing gives an empty window
  ⤷ same tuple, CRP           │                   ▓                                        │ CRP on Feb 21 ✓
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

```
                              │    Jan 1                            Jan 11                 │ result
                              │    |                                |                      │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = far-apart           │                                                            │ ✗ not selected
  resources                   │    ◆A41.5                           ◆N17.0                 │
                              │                                     ●CRP                   │
                              │                                        ●Hb                 │
  ⤷ the only tuple            │              end◄───────────────────►start                 │ earliest+3d is before latest
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

```
                              │         Jan 1  Jan 2   Jan 3                               │ result
                              │         |      |       |                                   │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = no-crp              │                                                            │ ✗ not selected
  resources                   │         ◆A41.5 ◆N17.0  ●Hb                                 │
  ⤷ tuple Jan 1 + Jan 2       │                ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                           │ Hb ✓, but the CRP group has nothing
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

## `ccdl-with-new-time-constraint-draft`

The realistic cohort, and the only one exercising both sides at once. All four patients share the
same inclusion data; they differ only in what they add.

The exclusion array is an **AND** of its two groups — an anticoagulant around the diagnosis *and* an
organ failure — so one alone does not exclude anyone. That is the opposite of how the same-looking
group behaves in `all-features`, where the two failures sit in one clause and conjoin instead.

Every patient also has a respiratory rate three days before the evaluation date, satisfying the
`now`-anchored group. That is off this timeline, which covers only the diagnosis-anchored part.

```
                              │      dx−3d   dx                       dx+10d               │ result
                              │      |       |                        |                    │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = included            │                                                            │ ✓ selected
  resources                   │      ●Weight ◇F00                     ●N06DA02             │
                              │           ●CRP                                             │
                              │           ●HR                                              │
  infection signs             │      ▓▓▓▓▓▓▓▓▓                                             │ CRP and HR inside dx−3d ✓
  donepezil                   │              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓            │ within 30d after dx ✓
  weight                      │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓            │ dx−7d onward ✓
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = anticoagulant-only  │                                                            │ ✓ selected
  resources                   │           ●CRP ◆B01AA04               ●N06DA02             │
                              │           ●HR◇F00                                          │
  exclusion: drug             │              ▓▓▓▓▓▓                                        │ anticoagulant is in range …
  exclusion: failure          │                                                            │ … but there is no organ failure, so the AND fails
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = excluded            │                                                            │ ✗ not selected
  resources                   │           ●CRP ◆B01AA04               ●N06DA02             │
                              │           ●HR◇F00                                          │
  exclusion: drug             │              ▓▓▓▓▓▓                                        │ anticoagulant in range ✓
  exclusion: failure          │                                                            │ N18.8 recorded in 2023 ✓ — both halves hold
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = no-heart-rate       │                                                            │ ✗ not selected
  resources                   │      ●Weight ◇F00                     ●N06DA02             │
                              │           ●CRP                                             │
  infection signs             │      ▓▓▓▓▓▓▓▓▓                                             │ clause 2 needs a heart rate; there is none
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```

## `ccdl-example-all-features-draft`

Every construct at once, and two inclusion arrays. Three patients take the first array; one takes the
second and never has the sepsis cascade at all.

`partial-exclusion` is the counterpart to `anticoagulant-only` above. Here the two organ failures are
**one clause with two criteria**, which conjoins on the exclusion side, so N18.8 alone is not enough
and the patient stays in. In `with-new-time-constraint` they are two clauses and disjoin. The two
examples look alike and mean different things.

```
                              │     dx                       op          Feb 25            │ result
                              │     |                        |           |                 │
══════════════════════════════╪════════════════════════════════════════════════════════════╪
Patient = main-path           │                                                            │ ✓ selected
  resources                   │     ◇K57.3  ●Hb              ◇5-455.3    ●8-85a.0          │
                              │                              ◇8-805.0                      │
                              │                                  ◆A41.5                    │
                              │                                     ◆N17.0                 │
  Hb between anchors          │     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                             │ dx → resection, Hb inside ✓
  ⤷ sepsis Feb 15             │                                  ▓▓▓▓▓▓▓                   │ AKI ✓ within 7d, CRP ✓ within 3d
  ⤷ AKI Feb 18                │                                     ▓▓▓▓▓▓▓▓▓▓▓            │ dialysis Feb 25 ✓
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = partial-exclusion   │                                                            │ ✓ selected
  resources                   │     ◇K57.3                    ◆B01AA04                     │
                              │                                  ◆A41.5                    │
  (rest as main-path)         │                                                            │ same inclusion data as main-path
  exclusion                   │                                                            │ drug ✓ but only N18.8; the clause needs K72 too
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = excluded            │                                                            │ ✗ not selected
  resources                   │     ◇K57.3                    ◆B01AA04                     │
                              │                                  ◆A41.5                    │
  (rest as main-path)         │                                                            │ same inclusion data as main-path
  exclusion                   │                                                            │ drug ✓ and N18.8 + K72 ✓ — excluded
──────────────────────────────┼────────────────────────────────────────────────────────────┼
Patient = specimen-path       │                                                            │ ✓ selected
  resources                   │     ◇K57.3                   ◇5-455.3        ●Hb           │
                              │     ▣Specimen                ◇8-805.0                      │
  array 2                     │                                                            │ specimen references the K57.3 condition ✓
  follow-up lab               │                              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓            │ resection → now, Hb inside ✓
══════════════════════════════╧════════════════════════════════════════════════════════════╧
```
