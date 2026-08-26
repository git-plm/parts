# Capacitor library cleanup plan

A plan for bringing `database/g-cap.csv` up to the standard the resistor library
already meets: correct data, consistent fields, series that group parts by
family, and a generated sweep of common values.

## TOC

<!-- vim-markdown-toc GFM -->

- [Where the library stands today](#where-the-library-stands-today)
- [Guiding rules](#guiding-rules)
  - [Two ways a part number stops being used](#two-ways-a-part-number-stops-being-used)
  - [What defines a series](#what-defines-a-series)
- [Phase 0: guardrails](#phase-0-guardrails)
- [Phase 1: field normalization](#phase-1-field-normalization)
- [Phase 2: incorrect data](#phase-2-incorrect-data)
- [Phase 3: incorrect variation codes](#phase-3-incorrect-variation-codes)
- [Phase 4: add the Status column](#phase-4-add-the-status-column)
- [Phase 5: consolidate series](#phase-5-consolidate-series)
- [Phase 6: split the mixed series](#phase-6-split-the-mixed-series)
- [Phase 7: generate the common-value sweep](#phase-7-generate-the-common-value-sweep)
- [Phase 8: document the conventions](#phase-8-document-the-conventions)
- [Suggested commit sequence](#suggested-commit-sequence)

<!-- vim-markdown-toc -->

## Where the library stands today

67 rows across 46 `NNNN` series. Most series hold a single part, so the `VVVV`
variation field is doing almost no work and there is no default capacitor for
any common combination. Compare the resistor library, where two series
(`RES-0000`, `RES-0001`) cover 1346 parts and any value a designer reaches for
already exists.

`check-csv.py` reports seven defects today. The audit behind this plan found
more that the current validator does not look for: variation codes that disagree
with the `Capacitance` column, MPNs that disagree with the `Voltage` and
`Material` columns, two part numbers sharing one MPN, and one MPN carried under
two part numbers.

The work splits into corrections that carry no risk to released BOMs (Phases
1-3), part number changes that do (Phases 5-6), and additions (Phase 7).

## Guiding rules

### Two ways a part number stops being used

The distinction drives which phases need a `Status` column and which do not.

**A wrong part number is corrected in place.** Where the variation code encodes
a capacitance the part does not have, the number was never a valid identifier
for anything. It is a typo, not a part with a history, so it is edited to the
right value and nothing is left behind. None of the seven affected numbers are
referenced anywhere in this repository, so nothing points at them to break.

**A valid part number that gets superseded keeps its row.** Where a part is
re-homed by an organizational decision, such as folding a series into another,
the number identified a real part correctly and something may still reference
it. Those rows stay and gain a note naming the replacement, so an old BOM still
resolves and a designer who finds the row is sent to the right part.

The second case needs a `Status` column, which `g-cap.csv` does not currently
have. The convention is already in use in the Zonit library, where the `Status`
column carries free text such as `Replaced by NCS325SN2T1G`. Here the IPN is the
database key, so notes point at IPNs instead of MPNs:

| `Status` value              | Meaning                                                 |
| --------------------------- | ------------------------------------------------------- |
| _(empty)_                   | Active. The normal state for nearly every row.          |
| `Replaced by CAP-XXXX-VVVV` | Do not use in new designs. Existing BOMs still resolve. |

Two supporting changes make the note visible where it matters:

- Add `Status` to the `CAP` entry in `gitplm.yml` under `visible`, so the note
  appears in the KiCad symbol chooser at the moment a designer would otherwise
  pick the retired part. A note nobody sees does not prevent reuse.
- Have `check-csv.py` verify that every `Replaced by` target actually exists in
  the file.

Adding a column rewrites every row in the file. That is a deliberate schema
change rather than incidental normalization, so it belongs in its own commit,
separate from any data correction. Because only Phases 5 and 6 need it, it lands
after the straight corrections rather than at the start.

### What defines a series

One `NNNN` series is one **package + voltage + dielectric** combination, and
`VVVV` sweeps capacitance within it. This follows `partnumbers.md`, which
defines `VVVV` as variations of parts sharing a datasheet or family.

The rule matters more for the phases below than the consolidation itself does.
Once it holds, a new value is a new row in an existing series rather than a new
`NNNN`, which is what stops the library drifting back to 46 series of one part
each.

Note that package is part of the key even when voltage and dielectric match.
`CAP-0031` and `CAP-0032` are both 16 V aluminium polymer but are different
Chemi-Con series in different case sizes, and they stay separate.

## Phase 0: guardrails

Do this first so later phases are checked as they land. Extend `check-csv.py`
with capacitor-specific checks:

- Decode the `VVVV` variation code and compare it against the `Capacitance`
  column. This alone catches the seven errors Phase 3 corrects.
- Flag a `Manufacturer` or `Material` value outside the canonical list agreed in
  Phase 1.

The decoder is short: `VVVV` of the form `DDDE` is `DDD x 10^E` pF, with a
leading `0` when only two significant digits are needed, and `R` marking a
decimal point for sub-10 pF values.

The `Replaced by` check comes later, in Phase 4, once the column it validates
exists.

## Phase 1: field normalization

No IPN changes, so no BOM impact. Safe to do in one pass.

`CLAUDE.md` says not to normalize existing rows as a side effect of adding a
part. Normalizing is the task here, not a side effect, so that rule does not
apply to this phase. It still applies to everyday part additions afterward.

**Broken footprints** — five rows use a colon where an underscore belongs, and
none of them resolve on disk:

```
Capacitor_SMD:C_0805:2012Metric  ->  Capacitor_SMD:C_0805_2012Metric
```

Affects `CAP-0008-0104`, `CAP-0015-0107`, `CAP-0023-0106`, `CAP-0025-0226`,
`CAP-0035-0107`.

**Manufacturer spellings** — 20 distinct spellings for 13 manufacturers. Pick
one form each and apply it:

| Canonical              | Currently also appears as                                                                 |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| `Murata`               | `Murata Electronics`, `Murata Electronics North America`, `Murata Manufacturing Co. Ltd.` |
| `Kemet`                | `KEMET`, `kEMET`, `Kemet Electronics`                                                     |
| `Yageo`                | `YAGEO`                                                                                   |
| `KYOCERA AVX`          | `AVX`                                                                                     |
| `Samsung`              | `Samsung Electro-Mechanics`                                                               |
| `Cal-Chip Electronics` | `Cal-Chip Electronics, Inc.`                                                              |

The Cal-Chip entry is also the file's only comma inside a field, which the repo
rules prohibit. Dropping `, Inc.` fixes both at once.

**Units and formats**

- Tolerance: `10.00%` -> `10%`, `20.00%` -> `20%`, `5.00%` -> `5%`.
- Voltage: `2.2KV` -> `2.2kV`, `3KV` -> `3kV`.
- Material: `COG` -> `C0G/NPO` (letter O to zero); settle `TANT POLY`,
  `TANT_POLY` and `Tant` on one form; same for `ALUM_POLY` and `Elec`.
- Capacitance: the column mixes `0.001uF`, `1000pF`, `2200pF` and `0.01uF`.
  Adopt one rule, such as pF below 1 nF and µF at and above it, and apply it
  throughout. This also makes the Phase 0 decoder check exact rather than
  approximate.
- Strip the trailing space in the `CAP-0014-0101` description.

**Sort order** — `CAP-0014-0150` currently follows `CAP-0014-06R8`. Re-sort the
file by IPN.

## Phase 2: incorrect data

These rows carry values that contradict their own MPN. Each is decodable from
the manufacturer part number, but confirm against the datasheet before editing,
per the repo rule that the datasheet is the source of truth.

| IPN             | MPN                  | Column      | File says | MPN says                                           |
| --------------- | -------------------- | ----------- | --------- | -------------------------------------------------- |
| `CAP-0015-0107` | `GRM21BR61C106KE15K` | Voltage     | 6.3V      | 16V (`1C`)                                         |
| `CAP-0039-0475` | `GRM188R61E475KE11D` | Voltage     | 6.3V      | 25V (`1E`)                                         |
| `CAP-0026-0225` | `GRM188R71A225KE15D` | Description | X5R       | X7R (`R7`); the `Material` column already says X7R |

Also in this phase:

- `CAP-0006-04R7` carries MPN `6035A4R7KAT2A`. AVX 0603 part numbers are 14
  characters and this one is 13, so the leading `0` appears to have been lost.
  Confirm `06035A4R7KAT2A` against the datasheet.
- `CAP-0041-0334` links a datasheet URL for `CL05Y105KP6VPN`, a different part.
  Replace with the datasheet for `CL03A334KA3NRNC`.
- `CAP-0005-0227` and `CAP-0005-0407` both carry MPN `SCCY68B407SSBLE` while
  describing 220 F and 400 F parts. Their footprints differ (`CX50B227` versus
  `CY68B407`), so the 220 F row most likely wants a different MPN. This needs
  the AVX SCC datasheet to resolve rather than a guess.

Run these before Phase 4. The two voltage corrections change which parts group
together, so consolidating first would produce the wrong groups.

## Phase 3: incorrect variation codes

Seven part numbers encode a capacitance that disagrees with the part. These are
corrected in place: edit the variation code to the right value and leave nothing
behind. A code that names a capacitance the part does not have never identified
anything, so there is no history to preserve, and a grep across this repository
finds no reference to any of the seven outside `g-cap.csv` itself.

Confirm that last point still holds at the time of the edit, and check any
project repository that consumes this library, since a reference from outside
would turn these into the superseded case instead.

| Current IPN     | Decodes to           | Actual value | Corrected IPN   |
| --------------- | -------------------- | ------------ | --------------- |
| `CAP-0003-220M` | _(not a valid code)_ | 220 µF       | `CAP-0003-0227` |
| `CAP-0012-0227` | 220 µF               | 22 µF        | `CAP-0012-0226` |
| `CAP-0013-0106` | 10 µF                | 1 µF         | `CAP-0013-0105` |
| `CAP-0015-0107` | 100 µF               | 10 µF        | `CAP-0015-0106` |
| `CAP-0019-0332` | 3.3 nF               | 0.033 µF     | `CAP-0019-0333` |
| `CAP-0023-0106` | 10 µF                | 1 µF         | `CAP-0023-0105` |
| `CAP-0030-0223` | 22 nF                | 0.22 µF      | `CAP-0030-0224` |

Two further rows the decoder flags are conventions rather than errors, and Phase
8 documents them instead:

- `CAP-0006-04R7` and `CAP-0014-06R8` use `R` as a decimal point for sub-10 pF
  values, mirroring the resistor `0R10` form.
- `CAP-0005-0227`, `CAP-0005-0407` and `CAP-0045-0127` are farad-scale
  supercapacitors, which the picofarad encoding cannot express.

## Phase 4: add the Status column

Everything up to here is a straight correction. From here on, part numbers that
identified their part correctly are superseded by an organizational decision, so
they keep their rows and need somewhere to record the replacement.

1. Add the `Status` column to `g-cap.csv`, empty on every existing row.
2. Add `Status` to the `CAP` `visible` list in `gitplm.yml`, and keep
   `database/#gplm.kicad_dbl` in step for anyone still on the ODBC path.
3. Add the `Replaced by` target check to `check-csv.py`.

Keep this separate from the phases either side of it. It touches every row in
the file without changing any part data, and mixing it with a correction would
bury that correction in the diff.

## Phase 5: consolidate series

Three groups hold one package, voltage and dielectric across more than one
`NNNN`. Merge each into the lowest-numbered series and retire the others with a
`Replaced by` note.

**0603 6.3 V X5R — `CAP-0042` into `CAP-0020`**

| Retire          | Replaced by     | Note                                         |
| --------------- | --------------- | -------------------------------------------- |
| `CAP-0042-0476` | `CAP-0020-0476` | Same MPN `GRM188R60J476ME15J` under two IPNs |
| `CAP-0042-0226` | `CAP-0020-0226` | New row in the surviving series              |

**1206 25 V X5R — `CAP-0034` into `CAP-0009`**

`CAP-0034-0226` (22 µF, `CL31A226KAHNNNE`) becomes `CAP-0009-0226`.

**0603 50 V C0G — `CAP-0044` into `CAP-0006`**

`CAP-0044-0180` (18 pF) becomes `CAP-0006-0180`. This merge only becomes visible
after Phase 1 normalizes `COG` to `C0G/NPO`.

Four rows move in total. Consolidation is the smallest part of this plan by
volume; its value is establishing the series rule that Phase 7 then builds on.

`CAP-0031` and `CAP-0032` are deliberately left separate, as noted above.

## Phase 6: split the mixed series

`CAP-0003` currently holds three unrelated families under one series number,
which is the inverse problem and needs a split rather than a merge:

| IPN             | Part                 | Family                              |
| --------------- | -------------------- | ----------------------------------- |
| `CAP-0003-0107` | `A700D107M006ATE018` | Kemet A700 aluminium polymer, 6.3 V |
| `CAP-0003-0157` | `T598V157M010ATE025` | Kemet T598 tantalum polymer, 10 V   |
| `CAP-0003-220M` | `10TPB220M`          | Panasonic POSCAP, 10 V              |

Three datasheets, three voltages, two chemistries. Allocate a new `NNNN` to two
of them, retire the old rows with `Replaced by` notes, and take the opportunity
to correct the `Material` column, which labels the A700 aluminium polymer part
as `TANT POLY`.

## Phase 7: generate the common-value sweep

This is where the library gains the most, and it is what the resistor side
already has via `scripts/generate_yageo_resistors.py`.

**Base the sweep on Murata GRM/GCM.** It is already the plurality of the file at
27 of 67 rows, it is the deepest-stocked MLCC family, and Samsung CL, Yageo CC
and TDK C are clean second sources against it.

**Scope it deliberately.** Resistors are one dimension, so one series covers
everything. Capacitors are four — package, voltage, dielectric, capacitance —
and sweeping the full cross product would produce thousands of rows, most of
them parts nobody stocks. Two constraints keep it useful:

- Generate E12, not E96. MLCCs are stocked in E12 and E6; an E96 capacitor sweep
  would be mostly unbuyable part numbers.
- Cover only the package, voltage and dielectric combinations the designs
  actually use. The existing series are the evidence for which those are.

A reasonable starting set, extending series that already exist rather than
minting new ones:

| Series     | Combination    | Range                      |
| ---------- | -------------- | -------------------------- |
| `CAP-0014` | 0402 50 V C0G  | 1 pF – 1 nF, E12           |
| `CAP-0019` | 0402 50 V X7R  | 100 pF – 100 nF, E12       |
| `CAP-0000` | 0603 50 V X7R  | 100 pF – 100 nF, E12       |
| `CAP-0020` | 0603 6.3 V X5R | 1, 2.2, 4.7, 10, 22, 47 µF |
| _(new)_    | 0603 16 V X5R  | 1, 2.2, 4.7, 10 µF         |

Confirm stock and lifecycle status per value as the generator runs. A generated
part number that cannot be bought is worse than no part number, because it looks
authoritative.

## Phase 8: document the conventions

Fold the decisions above back into the documentation so they survive.

In `partnumbers.md`, extend the capacitor section with:

- the `R` decimal-point form for sub-10 pF values, currently used but
  undocumented
- a convention for farad-scale supercapacitors, which the picofarad encoding
  cannot express
- the rule that one series is one package, voltage and dielectric

In `CLAUDE.md` and the `adding-parts` skill, add the instruction to extend an
existing series before allocating a new `NNNN`, and describe the `Status` column
and the `Replaced by` convention.

## Suggested commit sequence

Each phase stands alone and leaves the file valid, so they can land
independently and in order. Name paths explicitly rather than staging
everything.

1. Extend `check-csv.py` with the capacitor checks (Phase 0)
2. Normalize fields (Phase 1)
3. Correct contradicted data (Phase 2)
4. Correct variation codes in place (Phase 3)
5. Add the `Status` column and update `gitplm.yml` and `#gplm.kicad_dbl`
   (Phase 4)
6. Consolidate series (Phase 5)
7. Split `CAP-0003` (Phase 6)
8. Generate the sweep (Phase 7), one commit per series
9. Update documentation (Phase 8)

Commits 2 through 4 are corrections with nothing left behind, so the file is
smaller and cleaner after each. Commit 5 is the schema change, and 6 and 7 are
the only ones that retire a part number.

Run `check-csv.py --new-only database/g-cap.csv` after each step. None of these
commits change a symbol or footprint, so KiCad picks them up on the next
`gitplm http` reload with no further action.
