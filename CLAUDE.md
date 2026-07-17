# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## What this repo is

A KiCad parts library that is stored as data, not code. The CSV files in
`database/` **are** the database — [GitPLM](https://github.com/git-plm/gitplm)
reads them directly and serves them to KiCad over the
[HTTP libraries API](https://dev-docs.kicad.org/en/apis-and-binding/http-libraries/):

```
database/g-XXX.csv  ->  gitplm http (port 7654)  ->  KiCad
```

There is no build step and no database to regenerate. `gitplm http` watches
`database/` and reloads on save, so a CSV edit is live in KiCad immediately — no
restart, no library refresh.

The older `CSV -> SQLite3 -> ODBC -> KiCad` path (`parts_db_create` in
`envsetup.sh`, `database/#gplm.kicad_dbl`, `database/parts.sqlite`) is obsolete
and kept only for anyone who has not migrated. `parts.sqlite` is generated and
gitignored. Do not rebuild it unless the user says they are still on that path.

## The category triad

A part's three-letter category code (`RES`, `ICS`, `DIO`, ...) names three files
at once, and keeping them aligned is the point of the scheme:

| Concern    | Path                       |
| ---------- | -------------------------- |
| Data       | `database/g-XXX.csv`       |
| Symbols    | `symbols/g-XXX.kicad_sym`  |
| Footprints | `footprints/g-XXX.pretty/` |

Adding a category means adding a `database/g-XXX.csv`; `gitplm http` discovers
it on the next reload. There is no library list to register it in.

Column sets differ per category and are **not in a consistent order** — always
`head -1` the file before writing a row. A few categories (`ASY`, `CBL`, `ENC`,
`FAN`, `FST`) are BOM-only and have no `Symbol`/`Footprint` columns.

IPNs are `CCC-NNNN-VVVV` and are the database key. `partnumbers.md` is the full
specification.

## Commands

```bash
# Validate a CSV: column counts, IPN sort order, duplicate IPNs, and whether
# Symbol/Footprint references resolve on disk. Run from the repo root.
.claude/skills/adding-parts/scripts/check-csv.py --new-only database/g-reg.csv

# Serve the database to KiCad; watches database/ and reloads on save.
gitplm http

# Markdown formatting (prettier pinned by .prettier-version)
. envsetup.sh && parts_format          # write
. envsetup.sh && parts_format_check    # check only
```

`--new-only` diffs against `git HEAD` and reports only what your edit
introduced. Several older CSVs carry pre-existing defects (unsorted rows,
duplicate IPNs, broken references), so without the flag you cannot tell yours
from theirs.

Only markdown is formatted — CSV files are hand-maintained.

## Conventions that matter

- **Rows are sorted by IPN.** The IPN is the key; sorted files keep merges and
  diffs clean. Insert in sorted position rather than appending.
- **Never put a comma in a CSV field.** The comma is the delimiter. A comma in a
  field forces the field to be quoted, and quoted commas break `awk -F,`,
  `cut -d,`, spreadsheet imports, and any downstream reader that splits on the
  delimiter. `check-csv.py` accepts them, so nothing fails loudly; the damage
  surfaces later in whatever tool reads the file next. `Description` is where
  this comes up most, because it is the field with something to say. Write the
  field so the question never arises: separate specs with spaces, since each
  spec already carries its own unit.
- **Do not normalize existing rows as a side effect of adding a part.** Older
  rows carry inconsistent manufacturer spellings, commas, and truncated
  distributor strings. Match the file's most recent convention for new rows and
  leave the rest alone.
- **Never `git add -A`.** Name paths explicitly; the working tree often carries
  unrelated changes. 3D models belong in the separate `git-plm/3d-models` repo.
- Do not check CSV columns by splitting on commas — older quoted fields produce
  false errors. Use `check-csv.py` or Python's `csv` module.

## Adding parts

Use the `adding-parts` skill (`.claude/skills/adding-parts/SKILL.md`). It covers
the whole flow from an MPN: reading the datasheet, choosing the category,
assigning the IPN, reusing or authoring symbol and footprint, the 3D model, and
the CSV row. Two rules from it are worth stating up front, because they are the
ones that produce wrong parts:

- **The datasheet is the source of truth, not the request.** Requests routinely
  carry a spec from a neighbouring part in the series.
- **Never take specs from a summarized PDF.** Download the datasheet, confirm
  `file` reports a PDF (CDNs return HTML error pages under the `.pdf` name), and
  `Read` the pages as images. Summarizers fabricate pin counts and ratings with
  total confidence.

Reuse before you create: the KiCad standard library covers most symbols and
footprints, and a standard footprint carries its own 3D model.

## KiCad libraries on disk

Standard libraries are read from
`/usr/share/kicad/{symbols,footprints,3dmodels}` (`check-csv.py` honors
`KICAD_SYMBOL_DIR` / `KICAD_FOOTPRINT_DIR`). The `libs/` submodules are upstream
KiCad library checkouts kept for reference; they are not what KiCad loads.
