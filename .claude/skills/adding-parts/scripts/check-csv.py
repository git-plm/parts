#!/usr/bin/env python3
"""Validate parts CSV files.

Checks, per file:
  - every row has the same column count as the header
  - rows are sorted by IPN
  - no duplicate IPN (the IPN is the database key)
  - every Symbol and Footprint reference actually resolves on disk

Usage:
    check-csv.py database/g-reg.csv [...]
    check-csv.py database/g-*.csv
    check-csv.py --new-only database/g-reg.csv   # only defects absent from git HEAD

Several CSVs carry pre-existing defects. Use --new-only when adding a part, so
you see just the defects your own edit introduced. Run from the repo root.

Exits non-zero if any defect is reported.
"""

import csv
import os
import re
import subprocess
import sys

# Standard KiCad library locations. Override with KICAD_SYMBOL_DIR / KICAD_FOOTPRINT_DIR.
STD_SYMBOLS = os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")
STD_FOOTPRINTS = os.environ.get("KICAD_FOOTPRINT_DIR", "/usr/share/kicad/footprints")


def symbol_exists(ref: str) -> bool:
    """ref is 'Library:Symbol'. Local libs are symbols/<lib>.kicad_sym."""
    if ":" not in ref:
        return False
    lib, name = ref.split(":", 1)
    for path in (f"symbols/{lib}.kicad_sym", f"{STD_SYMBOLS}/{lib}.kicad_sym"):
        if os.path.exists(path):
            with open(path, errors="replace") as f:
                # Match (symbol "Name" ... at the top level of the library.
                if re.search(r'\(symbol\s+"%s"' % re.escape(name), f.read()):
                    return True
    return False


def footprint_exists(ref: str) -> bool:
    """ref is 'Library:Footprint'. Local libs are footprints/<lib>.pretty/."""
    if ":" not in ref:
        return False
    lib, name = ref.split(":", 1)
    for d in (f"footprints/{lib}.pretty", f"{STD_FOOTPRINTS}/{lib}.pretty"):
        if os.path.exists(f"{d}/{name}.kicad_mod"):
            return True
    return False


def defects(rows: list[list[str]], path: str) -> list[str]:
    out: list[str] = []
    if not rows:
        return [f"{path}: empty"]

    header = rows[0]
    ncols = len(header)
    col = {name: i for i, name in enumerate(header)}

    for lineno, row in enumerate(rows[1:], start=2):
        if len(row) != ncols:
            out.append(f"{path}: line {lineno}: {len(row)} fields, expected {ncols}")

    ipns = [r[0] for r in rows[1:] if r]

    for i in range(1, len(ipns)):
        if ipns[i] < ipns[i - 1]:
            out.append(f"{path}: not sorted: {ipns[i]} follows {ipns[i - 1]}")

    seen: set[str] = set()
    for ipn in ipns:
        if ipn in seen:
            out.append(f"{path}: duplicate IPN: {ipn}")
        seen.add(ipn)

    for lineno, row in enumerate(rows[1:], start=2):
        if len(row) != ncols:
            continue
        ipn = row[0]
        # A row may list alternate footprints separated by ';'; the first is the default.
        for field, exists in (("Symbol", symbol_exists), ("Footprint", footprint_exists)):
            if field not in col:
                continue
            value = row[col[field]].strip()
            if not value:
                continue
            for ref in value.split(";"):
                ref = ref.strip()
                if not ref:
                    continue
                # Alternates after the first are bare names in the same library.
                if ":" not in ref:
                    ref = value.split(";")[0].split(":", 1)[0] + ":" + ref
                if not exists(ref):
                    out.append(f"{path}: {ipn}: {field} does not resolve: {ref}")

    return out


def read_rows(path: str) -> list[list[str]]:
    with open(path, newline="") as f:
        return [r for r in csv.reader(f) if r]


def read_rows_at_head(path: str) -> list[list[str]] | None:
    try:
        blob = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None  # new file, not in HEAD
    return [r for r in csv.reader(blob.splitlines()) if r]


def main() -> int:
    args = sys.argv[1:]
    new_only = "--new-only" in args
    paths = [a for a in args if not a.startswith("-")]

    if not paths:
        print(__doc__)
        return 2

    failed = False
    for path in paths:
        found = defects(read_rows(path), path)

        if new_only:
            head = read_rows_at_head(path)
            if head is not None:
                baseline = set(defects(head, path))
                found = [d for d in found if d not in baseline]

        for d in found:
            print(d)
            failed = True
        if not found:
            n = len(read_rows(path)) - 1
            print(f"{path}: ok ({n} parts)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
