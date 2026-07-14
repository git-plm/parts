---
name: adding-parts
description: Use when adding a component to this parts library from a manufacturer and part number (MPN) - assigns the IPN, picks the category CSV, links the datasheet, reuses or creates the KiCad symbol and footprint, and links a 3D model.
---

# Adding Parts

## Overview

Turn a manufacturer + MPN into a complete library part: one row in the right
`database/g-XXX.csv`, a verified datasheet link, a symbol, a footprint, and a
3D model.

**Reuse before you create.** The KiCad standard library covers most symbols and
footprints. A standard footprint also carries its own 3D model, so choosing one
correctly removes three tasks at once. Author a symbol or footprint only when
nothing standard fits.

**The datasheet is the source of truth, not the request.** The MPN, package, and
specs you are handed are frequently wrong in some detail. Confirm every value
against the manufacturer's datasheet before writing a row.

Run every command from the repo root.

## Workflow

### 1. Read the datasheet

**Never take component specifications from a text summary of a PDF.** WebFetch
and similar summarizers fabricate pin counts, package codes, current ratings,
and dimensions with total confidence. This has produced a 6-pin symbol for an
8-pin part.

Download the PDF and read the pages as images. **Send a browser user-agent and
confirm you actually got a PDF:**

```bash
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
curl -sSL -A "$UA" -o /tmp/part.pdf "<manufacturer datasheet url>"
file /tmp/part.pdf    # must say "PDF document"
```

Manufacturer CDNs (Nexperia and others sit behind Akamai) reject curl's default
user-agent with a 403 and return a several-hundred-byte HTML "Access Denied"
page. `curl -o part.pdf` saves that HTML *under the .pdf name* without error. If
you skip the `file` check you will be reading an error page and inventing specs
from nothing. Always confirm before you read.

Then use `Read` on `/tmp/part.pdf` with a `pages` range. Read the actual pages
for:

- **Pin functions table** - pin numbers, names, and electrical types
- **Device comparison table** - which orderable MPN is which, and how siblings differ
- **Package outline and recommended land pattern** - usually the last few pages

Confirm the package, the pinout, and every spec that lands in a CSV column. Web
search is fine for *finding* the datasheet and for distributor descriptions; it
is not acceptable for numbers.

The **packing suffix** (`,115`, `-T`, `TR`) is usually *not* in the datasheet -
it comes from the distributor or product page. Carry the suffix the request
supplies, and match the convention of sibling rows in the category.

**When the request and the datasheet disagree, the datasheet wins - write what
it says, and tell the user.** Requests routinely carry a spec from a
neighbouring part in the series.

But distinguish two cases. If the disagreement is a *detail* (a current rating
or body size that is simply wrong), write the datasheet value and note it. If
the disagreement implies **a different part** - the MPN decodes to a 30V device
and the user asked for 20V - then it is unclear which part they want to buy.
Stop and ask before committing.

**Watch for package aliases.** Manufacturers and distributors often use
different names for the same physical package (TI's `VSON-HR (DLC)` is sold as
`SOT-583`). KiCad may ship *both* names as separate footprints, in different
libraries, with different pad geometry. Use the package name from the
manufacturer's own drawing, and pick the footprint by pad geometry (step 5), not
by name matching.

Then check the part is not already in the library:

```bash
grep -ri "<MPN>" database/                    # exact part
grep -ri "<base MPN, no suffix>" database/    # sibling variations
```

A hit on a sibling usually means the new part is a **variation** of an existing
IPN: it shares the `NNNN` and takes a new `VVVV`.

Prefer the manufacturer's own datasheet URL; a distributor link is acceptable
when there is no stable manufacturer PDF. Verify it resolves:

```bash
curl -sSI -o /dev/null -w '%{http_code}\n' "<datasheet url>"
```

### 2. Choose the category

The category determines the CSV file (`database/g-XXX.csv`), the symbol library
(`symbols/g-XXX.kicad_sym`), and the footprint library
(`footprints/g-XXX.pretty`). Keeping those three names aligned is the point of
the scheme.

| Code  | Takes                                               |
| ----- | --------------------------------------------------- |
| `ANA` | op-amps, comparators, A/D, D/A                      |
| `ART` | artwork: test points, fiducials, logos              |
| `CAP` | capacitors                                          |
| `CON` | connectors, wire, heatshrink                        |
| `CPD` | circuit protection: TVS, ESD, fuses                 |
| `DIO` | diodes                                              |
| `ICS` | integrated circuits not covered by a finer category |
| `IND` | inductors, transformers, ferrites                   |
| `MCU` | microcontrollers                                    |
| `MPU` | SOC, SOM, SBC                                       |
| `OPT` | optical: optoisolators, LEDs, phototransistors      |
| `OSC` | oscillators, crystals                               |
| `PWR` | power switches, relays, load switches               |
| `REG` | voltage regulators, linear and switching            |
| `RES` | resistors                                           |
| `RFM` | RF modules and ICs                                  |
| `SWI` | switches                                            |
| `XTR` | transistors, FETs                                   |

**Pick the most specific category that fits.** A buck converter is `REG`, not
`ICS`. A USB power switch is `PWR`, not `ICS`. When two genuinely fit, `grep`
for a comparable part and follow what it did.

`partnumbers.md` lists further codes (`SEN`, `MEM`, ...) that have no CSV yet.
Creating one is a new-category change - see below.

**BOM-only categories.** `ASY`, `CBL`, `ENC`, `FAN`, `FST` have no `Symbol` or
`Footprint` column. They are items that never appear in a schematic, and they
are deliberately absent from `GPLMLIBS` in `envsetup.sh` and from
`database/#gplm.kicad_dbl`. For these, steps 4-6 do not apply: fill in
`IPN,MPN,Manufacturer,Description,Datasheet` and go to step 7.

### 3. Assign the IPN

Format is `CCC-NNNN-VVVV`. Rationale is in `partnumbers.md`; the operative rules:

**`NNNN` - the part family.** One `NNNN` per datasheet/family. A different
datasheet means a new `NNNN`, even at an identical value: a 4.7uH Bourns
inductor does not share `NNNN` with a 4.7uH Panasonic inductor.

One datasheet covering *several distinct devices* (different die, pin count, or
pinout) is the exception: give each device its own `NNNN`. `VVVV` is for
variations of one device, not for different devices that happen to share a PDF.

Next free number in the category:

```bash
grep -o '^IND-[0-9]\{4\}' database/g-ind.csv | sort -u | tail -1
```

**`VVVV` - the variation within that family.** Encode the parameter that varies
most across the family:

| Category        | `VVVV` encodes                      | Example                     |
| --------------- | ----------------------------------- | --------------------------- |
| `RES`           | E96/E24 resistance code             | `1002` = 10k, `0R10` = 0.1R |
| `CAP`           | 3-digit pF code                     | `104` = 0.1uF               |
| `IND`           | inductance                          | `04R7` = 4.7uH              |
| `CON`           | pin count                           | `0012` = 12 positions       |
| `DIO`           | voltage **for Zeners only**         | `04V7` = 4.7V Zener         |
| `REG`           | **fixed** output voltage            | `03V3` = 3.3V               |
| `OSC`           | frequency                           | `0256` = 25.6MHz            |
| everything else | sequential from `0001`              | `0001`, `0002`, ...         |

**When a part has no natural variation parameter, use `0001`.** That is what
`ICS`, `MCU`, `XTR`, `CPD`, `RFM`, `PWR`, `ANA`, `OPT`, and `MPU` do for
single-variant parts. Do not use `0000`; a few old rows use it, but `0001` is
the established convention.

The voltage encodings apply **only where the voltage is the varying parameter**:

- A **Schottky or rectifier** diode is not a Zener family. Every non-Zener row in
  `g-dio.csv` uses `0001`, including a 30V part. Use `0001`.
- A **regulator with adjustable or resistor-selectable output** has no single
  fixed voltage. Use `0001`, with `ADJ` in the `Voltage` column.

When in doubt, `grep` the category CSV for a comparable part and follow it. The
data is the authority, not this table.

### 4. Resolve the symbol

Search the standard library first:

```bash
grep -l "<part or family name>" /usr/share/kicad/symbols/*.kicad_sym
grep -o '(symbol "[^"]*"' /usr/share/kicad/symbols/<Lib>.kicad_sym | grep -i <name>
```

Most passives and discretes need nothing custom:

| Part          | Symbol                                        |
| ------------- | --------------------------------------------- |
| Resistor      | `Device:R_US`                                  |
| Capacitor     | `Device:C`                                     |
| Inductor      | `Device:L`                                     |
| Schottky/Zener | `Device:D_Schottky`, `Device:D_Zener`         |
| Crystal       | `Device:Crystal_GND24`                         |
| BJT           | `Transistor_BJT:Q_NPN_BEC`, `Transistor_PNP_BEC` |
| MOSFET        | `Transistor_FET:Q_NMOS_GSD`                    |

**Transistors are not in `Device`.** KiCad moved them to `Transistor_BJT` and
`Transistor_FET`. Existing `g-xtr.csv` rows still say `Device:Q_NPN_BEC` and are
broken against KiCad 10 - do not copy them. `check-csv.py` catches this.

Write the reference as `Library:Symbol` for a standard symbol, or `g-XXX:Name`
for one in this repo. **Confirm it resolves before writing the row** - a
plausible-looking library prefix is the easiest mistake to make here, and it
survives every check except `check-csv.py`.

If nothing fits, create the symbol in `symbols/g-XXX.kicad_sym`. See
`references/creating-symbols-footprints.md`.

### 5. Resolve the footprint

Search the standard library first:

```bash
ls /usr/share/kicad/footprints/ | grep -i <package family>
ls /usr/share/kicad/footprints/<Lib>.pretty/ | grep -i <package>
```

**When two standard footprints look equally plausible** - which happens whenever
a package has aliases - break the tie in this order:

1. Compare each candidate's pad geometry against the datasheet's recommended
   land pattern and take the closer match. This is the deciding test.
2. If the upstream KiCad symbol for this part or its closest sibling declares
   `ki_fp_filters`, that is a strong second opinion - upstream already made this
   call.
3. Report the choice to the user with both candidates and the datasheet's land
   pattern dimensions. Do not silently discard the one the request named.

A row may list alternates separated by `;`. The first is the default; the rest
appear in KiCad's footprint picker, and are used for hand-solder variants:

```
Resistor_SMD:R_0603_1608Metric;R_0603_1608Metric_Pad0.98x0.95mm_HandSolder
```

If nothing fits, create the footprint in `footprints/g-XXX.pretty/`. See
`references/creating-symbols-footprints.md`.

### 6. Resolve the 3D model

**Standard footprint: nothing to do.** Every standard KiCad footprint already
embeds a `(model "${KICAD10_3DMODEL_DIR}/...")` reference and ships the STEP
file. Confirm and move on:

```bash
grep model /usr/share/kicad/footprints/<Lib>.pretty/<Footprint>.kicad_mod
```

**Custom footprint: you must supply the model.** 3D models live in a *separate*
repository (`git-plm/3d-models`), referenced through the `GITPLM_3DMODELS`
environment variable. See `references/creating-symbols-footprints.md`.

### 7. Write the CSV row

Read the header first - **columns differ per category and are not in a
predictable order** (`g-reg.csv` puts `Voltage,Current` *before* `Symbol`):

```bash
head -1 database/g-reg.csv
```

- **Insert in IPN-sorted position.** The IPN is the database key and sorted files
  diff cleanly. Only the highest IPN belongs at the end - do not blindly append.
- **Match the file's existing quoting style.** `g-con.csv`, `g-swi.csv`, and
  `g-fan.csv` quote every field; the rest quote only fields containing a comma or
  a double quote.
- **Reuse the existing spelling of the manufacturer.** `grep` the category file
  first. Where the file already contradicts itself (`g-dio.csv` has `onsemi`,
  `On Semi`, and `OnSemi`; `g-reg.csv` has both `TI` and `Texas Instruments`),
  follow the most recent row rather than adding a fourth spelling. Do not
  normalize the existing rows as a side effect of adding a part.
- **Description**: most distinguishing specs first, short enough to read in the
  schematic chooser, e.g. `Buck regulator, 750mA, 1.8-6.5V in, adjustable`.
  Some older rows hold raw distributor strings truncated mid-word
  (`FIXED IND 6.8UH 8.5A 23.3MOHM SM`). Do not imitate those; write a clean
  description.
- **One value per column.** Where a part has two legitimate ratings for a single
  column - an inductor's I_rms and I_sat, for instance - put the conservative
  continuous rating in the column and both in the `Description`.
- Leave a column empty when the datasheet does not specify it. Do not invent
  values.

### 8. Validate

```bash
# Column count, IPN sort order, duplicate IPNs, and whether the Symbol and
# Footprint references actually resolve on disk.
.claude/skills/adding-parts/scripts/check-csv.py --new-only database/g-reg.csv

# Rebuild the SQLite database.
. envsetup.sh && parts_db_create && echo "db rebuilt"
```

`--new-only` diffs against `git HEAD` and reports just the defects your edit
introduced. Several CSVs carry pre-existing defects (unsorted rows, duplicate
IPNs, broken footprint references); without the flag you cannot tell yours from
theirs. **It must report `ok`.**

Do not check columns by splitting on commas (`awk -F,`, `cut -d,`) -
`Description` legitimately contains quoted commas, so a naive split reports
false errors.

`parts_db_create` is silent on success and is a weak validator - SQLite will
import some malformed rows without complaint. `check-csv.py` is the real test.

Then tell the user to **restart KiCad entirely**; it does not reload database
libraries any other way.

### 9. Commit

Commit only the files for this part. Check `git status` first - the working tree
may already carry unrelated changes, and they should not be swept in.

**Never `git add -A`.** Name the paths explicitly. A part addition typically
touches `database/g-XXX.csv` alone, plus `symbols/g-XXX.kicad_sym` and
`footprints/g-XXX.pretty/*.kicad_mod` when custom CAD was authored.
`database/parts.sqlite` is generated and is not committed.

A 3D model is committed to the *separate* `3d-models` repository, not this one.

## Adding a new category

Only when the part genuinely fits no existing category:

1. Create `database/g-XXX.csv` with a header, copying the column set from the
   closest existing category.
2. Add `XXX` to the `CCC` table in `partnumbers.md` if absent.
3. **Only if the category has symbols and footprints** (it appears in schematics):
   - add the lowercase code to `GPLMLIBS` in `envsetup.sh`
   - add a library block to `database/#gplm.kicad_dbl`, copying an existing block
     and adjusting `name`, `table`, and `fields` to the new columns
   - create `symbols/g-XXX.kicad_sym` and `footprints/g-XXX.pretty/` as needed

   BOM-only categories skip all of this - which is why `ENC`, `FST`, `CBL`,
   `FAN`, and `ASY` appear in neither file.
4. Verify the JSON still parses: `jq . 'database/#gplm.kicad_dbl'`

## Checklist

- [ ] Datasheet PDF downloaded and **read as pages**, not summarized
- [ ] MPN, package, pinout, and specs confirmed against it
- [ ] Discrepancies with the request reported to the user
- [ ] MPN not already in `database/`
- [ ] Category chosen: the most specific one that fits
- [ ] IPN assigned: new `NNNN` for a new datasheet, correct `VVVV` encoding, `0001` if no natural variation
- [ ] Symbol: standard library searched before authoring
- [ ] Footprint: standard library searched before authoring; alias ties broken on pad geometry
- [ ] 3D model: confirmed present (standard footprint) or sourced and referenced (custom)
- [ ] Row inserted in sorted position; quoting style, column count, and manufacturer spelling match the file
- [ ] `check-csv.py --new-only` reports `ok`
- [ ] `parts_db_create` succeeds; datasheet URL returns 200
- [ ] Only this part's files committed
- [ ] User told to restart KiCad
