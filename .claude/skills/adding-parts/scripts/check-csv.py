#!/usr/bin/env python3
"""Validate parts CSV files.

Checks, per file:
  - every row has the same column count as the header
  - every IPN is CCC-NNNN-VVVV in capitals, digits and hyphen
  - the IPN category matches the file it is in
  - rows are sorted by IPN
  - no duplicate IPN (the IPN is the database key)
  - every Symbol and Footprint reference actually resolves on disk
  - no comma inside a field (the comma is the delimiter)
  - no field padded with a leading or trailing space
  - Datasheet is an https URL
  - Manufacturer, Material and the spec columns do not vary in spelling
  - Material does not spell C0G with a letter O
  - a 'Replaced by <IPN>' Status names a part that exists in the file
  - for CAP files, the IPN variation code matches the Capacitance column
  - for RES files, the IPN variation code matches the Resistance column

Checks across every file named on the command line:
  - one spelling per manufacturer
  - no MPN carried by two parts that are both still live

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

# CCC-NNNN-VVVV, in capitals, digits and hyphen. See partnumbers.md.
IPN_RE = re.compile(r"^[A-Z]{3}-[0-9]{4}-[0-9A-Z]{4}$")

# Columns that carry a measured value with a unit. These drift the same way
# manufacturer names do -- 25V beside 25v, 4.75K beside 4.75k -- and the drift
# is what makes a column impossible to group or sort on later.
SPEC_COLUMNS = (
    "Voltage", "Current", "Power", "Tolerance", "Resistance", "Capacitance",
    "Inductance", "Frequency", "Stability", "Load", "Wavelength", "Color",
    "V-forward", "I-forward-max", "Form", "Pins",
)


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


# --- capacitance ---------------------------------------------------------
#
# The IPN variation field encodes capacitance the way vendors do: MME, where MM
# is the mantissa and E the number of zeros, in pF. The leading digit is
# normally 0 because two significant figures is enough, and 'R' stands in for a
# decimal point on sub-10pF values (04R7 = 4.7pF), mirroring the resistor 0R10
# form. See partnumbers.md.
#
# Farad-scale parts (supercapacitors, lithium-ion capacitors) need far more
# range than the exponent digit allows, so they use 'F' the same way: as a
# terminator on whole values (220F) and a decimal point on fractional ones
# (01F5 = 1.5F). An 'F' anywhere in the field means the value is in farads.

SI = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "": 1.0}


def parse_capacitance(text: str) -> float | None:
    """'0.1uF' / '100pF' / '220F' -> farads. None if unparseable."""
    m = re.fullmatch(r"([\d.]+)\s*([pnuµm]?)F", text.strip(), re.I)
    if not m:
        return None
    try:
        return float(m.group(1)) * SI[m.group(2).lower()]
    except (ValueError, KeyError):
        return None


def decode_variation(code: str) -> float | None:
    """IPN variation field -> farads. None if it is not a capacitance code."""
    if "F" in code:
        digits = code[:-1] if code.endswith("F") else code.replace("F", ".")
        try:
            return float(digits)
        except ValueError:
            return None
    if re.fullmatch(r"\d[\dR]R?\d", code) and "R" in code:
        return float(code.replace("R", ".")) * 1e-12
    if not re.fullmatch(r"\d{4}", code):
        return None
    mantissa = int(code[1:3]) if code[0] == "0" else int(code[0:3])
    return mantissa * (10 ** int(code[3])) * 1e-12


def show_farads(value: float) -> str:
    for suffix, scale in (("F", 1), ("mF", 1e-3), ("uF", 1e-6), ("nF", 1e-9), ("pF", 1e-12)):
        if value >= scale:
            return f"{value / scale:g}{suffix}"
    return f"{value}F"


# --- resistance ----------------------------------------------------------
#
# Two encodings are in use, and both are self-consistent.
#
# partnumbers.md documents the EIA 4-digit industry code: three significant
# digits followed by the number of zeros, in ohms, with a leading 0 marking a
# two-digit mantissa. 1002 = 10k, 4751 = 4.75k, 0220 = 22R. The one-off series
# RES-0003 through RES-0013 follow it.
#
# The generated value sweeps in RES-0000 and RES-0001 read the same digits two
# decades lower: 1000 = 1R, 1003 = 1k, 4751 = 47.5R. That is 1,346 of the 1,359
# resistors in the library.
#
# A part number is never reused, so neither encoding can be renumbered away.
# This check therefore accepts either and reports only the rows that decode to
# the stated resistance under neither, which is where a real transcription
# error shows up. It reports the split itself once per file, because a code
# that means two things in one file is worth seeing even though resolving it
# is a documentation decision rather than an edit.
#
# 'R' is the decimal point on sub-ohm and fractional values (0R10, 25R5), and a
# trailing 'm' marks milliohms (010m = 10 mOhm, 8R3m = 8.3 mOhm), mirroring the
# way 'F' terminates the farad-scale capacitor codes.

RESISTANCE_SI = {"": 1.0, "R": 1.0, "K": 1e3, "M": 1e6, "G": 1e9}


def parse_resistance(text: str) -> float | None:
    """'4.75K' / '100' / '8.3m' -> ohms. None if unparseable."""
    t = text.strip().replace("\u03a9", "").replace("ohms", "").replace("ohm", "").strip()
    m = re.fullmatch(r"([\d.]+)\s*([kKmMGR]?)", t)
    if not m:
        return None
    scale = 1e-3 if m.group(2) == "m" else RESISTANCE_SI.get(m.group(2).upper())
    if scale is None:
        return None
    try:
        return float(m.group(1)) * scale
    except ValueError:
        return None


def decode_resistance(code: str) -> tuple[float | None, float | None]:
    """IPN variation field -> (industry ohms, sweep ohms).

    Both elements are None together when the code is not a resistance at all.
    The milliohm and R forms read the same under either encoding, so they come
    back as a matched pair, which is how the caller recognizes a code that is
    no evidence either way.
    """
    c = code.strip()
    if c.endswith("m"):
        body = c[:-1].replace("R", ".")
        try:
            value = float(body) * 1e-3
        except ValueError:
            return None, None
        return value, value
    if "R" in c:
        try:
            value = float(c.replace("R", "."))
        except ValueError:
            return None, None
        return value, value
    if not re.fullmatch(r"\d{4}", c):
        return None, None
    mantissa = int(c[1:3]) if c[0] == "0" else int(c[0:3])
    industry = mantissa * (10 ** int(c[3]))
    return industry, industry * 0.01


def show_ohms(value: float) -> str:
    for suffix, scale in (("G", 1e9), ("M", 1e6), ("K", 1e3), ("", 1), ("m", 1e-3)):
        if value >= scale:
            return f"{value / scale:g}{suffix}"
    return f"{value}"


def close(a: float, b: float) -> bool:
    return abs(a - b) <= 0.02 * max(abs(a), abs(b), 1e-30)


def normalize(text: str) -> str:
    """Collapse spelling variants so near-duplicates group together."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def normalize_value(text: str) -> str:
    """Collapse case and spacing in a measured value, but keep the decimal point.

    A name may differ by punctuation and still be the same manufacturer. A
    value may not: 1.02 and 102 are two resistors, so the looser normalize()
    above would report every decade of a value sweep as a spelling variant.
    """
    return re.sub(r"\s", "", text.lower())


def is_live(row: list[str], status_col: int | None) -> bool:
    """A part is live until its Status retires it in favour of another IPN."""
    if status_col is None or status_col >= len(row):
        return True
    return not re.match(r"\s*Replaced by\s", row[status_col], re.I)


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

    # The IPN is the database key, so a malformed one is the defect that
    # reaches a BOM. The category has to match the file as well: g-res.csv
    # holding a CAP number would put the part in the wrong symbol library.
    category = os.path.basename(path)[2:5].upper()
    for lineno, ipn in enumerate(ipns, start=2):
        if not IPN_RE.match(ipn):
            out.append(f"{path}: line {lineno}: IPN is not CCC-NNNN-VVVV in capitals: {ipn}")
        elif ipn[:3] != category:
            out.append(f"{path}: line {lineno}: IPN category {ipn[:3]} does not match {category}: {ipn}")

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

    # The comma is the delimiter. A field containing one has to be quoted, and
    # the quoting breaks awk -F, cut -d, and spreadsheet imports downstream.
    for lineno, row in enumerate(rows[1:], start=2):
        for i, value in enumerate(row):
            if "," in value:
                name = header[i] if i < ncols else f"field {i}"
                out.append(f"{path}: line {lineno}: comma in {name}: {value!r}")

    # A padded field looks identical in a spreadsheet and sorts and groups as a
    # different value everywhere else. 'STMicroelectronics ' is not the same
    # manufacturer as 'STMicroelectronics' to anything that does not trim.
    for lineno, row in enumerate(rows[1:], start=2):
        for i, value in enumerate(row):
            if value.strip() and value != value.strip():
                name = header[i] if i < ncols else f"field {i}"
                out.append(f"{path}: line {lineno}: {name} padded with whitespace: {value!r}")

    # The datasheet is the source of truth for every spec in the row, so the
    # link has to be one a browser can open. A note in the field reads as a
    # link until someone clicks it.
    if "Datasheet" in col:
        for lineno, row in enumerate(rows[1:], start=2):
            if len(row) != ncols:
                continue
            url = row[col["Datasheet"]].strip()
            has_mpn = "MPN" not in col or row[col["MPN"]].strip()
            if not url:
                if has_mpn:
                    out.append(f"{path}: {row[0]}: no Datasheet")
            elif not url.startswith(("http://", "https://")):
                out.append(f"{path}: {row[0]}: Datasheet is not a URL: {url!r}")
            elif url.startswith("http://"):
                out.append(f"{path}: {row[0]}: Datasheet is http, not https: {url}")

    # One spelling per manufacturer, one per dielectric, one per unit. Rather
    # than police a list that would go stale, flag values that differ only in
    # case, spacing or punctuation from another value in the same file. Names
    # and measured values need different notions of "only" -- see the two
    # normalizers above.
    naming = [(f, normalize) for f in ("Manufacturer", "Material")]
    naming += [(f, normalize_value) for f in SPEC_COLUMNS]
    for field, collapse in naming:
        if field not in col:
            continue
        variants: dict[str, set[str]] = {}
        for row in rows[1:]:
            if len(row) == ncols and row[col[field]].strip():
                value = row[col[field]].strip()
                variants.setdefault(collapse(value), set()).add(value)
        for spellings in variants.values():
            if len(spellings) > 1:
                out.append(f"{path}: {field} written {len(spellings)} ways: {sorted(spellings)}")

    # C0G is a zero, not a letter O. The two look identical in most fonts, so
    # nothing else will catch this.
    if "Material" in col:
        for row in rows[1:]:
            if len(row) == ncols and re.search(r"\bCOG\b", row[col["Material"]], re.I):
                out.append(f"{path}: {row[0]}: Material spells C0G with a letter O: {row[col['Material']]}")

    # A retired part keeps its row so the number is permanently spent: the row
    # is the record that it must never be issued again, and the duplicate-IPN
    # check above is what enforces that. Two things can still go wrong.
    #
    # The replacement has to exist, or the note sends a designer nowhere, and it
    # must not itself be retired, or the note sends them to another dead end.
    if "Status" in col:
        retired = {
            row[0]
            for row in rows[1:]
            if len(row) == ncols and re.match(r"\s*Replaced by\s", row[col["Status"]], re.I)
        }
        for row in rows[1:]:
            if len(row) != ncols:
                continue
            m = re.match(r"\s*Replaced by\s+(\S+)", row[col["Status"]], re.I)
            if not m:
                continue
            if m.group(1) in retired:
                out.append(
                    f"{path}: {row[0]}: Status points at {m.group(1)}, which is itself retired"
                )
            if m.group(1) not in seen:
                out.append(f"{path}: {row[0]}: Status names a part that does not exist: {m.group(1)}")

    # Capacitor variation codes encode the value; a code that disagrees with the
    # Capacitance column means one of the two is wrong.
    if "Capacitance" in col:
        for row in rows[1:]:
            if len(row) != ncols or not row[0].startswith("CAP-"):
                continue
            parts = row[0].split("-")
            if len(parts) != 3:
                continue
            stated = parse_capacitance(row[col["Capacitance"]])
            if stated is None:
                out.append(f"{path}: {row[0]}: cannot parse Capacitance: {row[col['Capacitance']]!r}")
                continue
            coded = decode_variation(parts[2])
            if coded is None:
                out.append(f"{path}: {row[0]}: variation code is not a capacitance: {parts[2]!r}")
            elif abs(coded - stated) > 0.02 * max(coded, stated):
                out.append(
                    f"{path}: {row[0]}: variation code says {show_farads(coded)}, "
                    f"Capacitance says {row[col['Capacitance']]}"
                )

    # Resistor variation codes encode the value too, under either of the two
    # encodings described above. A row that matches neither has a code and a
    # Resistance column that disagree however you read them.
    if "Resistance" in col:
        readings: set[str] = set()
        for row in rows[1:]:
            if len(row) != ncols or not row[0].startswith("RES-"):
                continue
            parts = row[0].split("-")
            if len(parts) != 3:
                continue
            stated = parse_resistance(row[col["Resistance"]])
            if stated is None:
                out.append(f"{path}: {row[0]}: cannot parse Resistance: {row[col['Resistance']]!r}")
                continue
            industry, sweep = decode_resistance(parts[2])
            if industry is None:
                out.append(f"{path}: {row[0]}: variation code is not a resistance: {parts[2]!r}")
            elif close(industry, stated):
                if not close(industry, sweep):
                    readings.add("industry")
            elif close(sweep, stated):
                readings.add("sweep")
            else:
                out.append(
                    f"{path}: {row[0]}: variation code says {show_ohms(industry)} "
                    f"(or {show_ohms(sweep)} scaled), Resistance says {row[col['Resistance']]}"
                )
        if len(readings) > 1:
            out.append(
                f"{path}: two resistance encodings in use: the EIA code partnumbers.md "
                f"documents and the value sweeps' form two decades below it"
            )

    return out


def cross_defects(loaded: dict[str, list[list[str]]]) -> list[str]:
    """Defects that only show up when several files are read together.

    A single file cannot see that onsemi is spelled four ways across five
    categories, or that the same connector holds an IPN in two of them.
    """
    out: list[str] = []

    spellings: dict[str, set[str]] = {}
    homes: dict[str, set[str]] = {}
    mpns: dict[str, list[str]] = {}

    for path, rows in sorted(loaded.items()):
        if not rows:
            continue
        header = rows[0]
        ncols = len(header)
        col = {name: i for i, name in enumerate(header)}
        status = col.get("Status")
        for row in rows[1:]:
            if len(row) != ncols:
                continue
            if "Manufacturer" in col and row[col["Manufacturer"]].strip():
                value = row[col["Manufacturer"]].strip()
                spellings.setdefault(normalize(value), set()).add(value)
                homes.setdefault(normalize(value), set()).add(os.path.basename(path))
            if "MPN" in col and row[col["MPN"]].strip() and is_live(row, status):
                mpns.setdefault(row[col["MPN"]].strip().upper(), []).append(row[0])

    for key, names in sorted(spellings.items()):
        if len(names) > 1:
            out.append(
                f"Manufacturer written {len(names)} ways across "
                f"{sorted(homes[key])}: {sorted(names)}"
            )

    # Two live parts sharing an MPN are the same physical component ordered
    # under two numbers. Retiring one with 'Replaced by' is the fix, which is
    # why a retired row is not counted here.
    for mpn, owners in sorted(mpns.items()):
        if len(set(owners)) > 1:
            out.append(f"MPN {mpn} is carried by {len(set(owners))} live parts: {sorted(set(owners))}")

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
    current: dict[str, list[list[str]]] = {}
    baseline_rows: dict[str, list[list[str]]] = {}

    for path in paths:
        rows = read_rows(path)
        current[path] = rows
        found = defects(rows, path)

        if new_only:
            head = read_rows_at_head(path)
            baseline_rows[path] = head or []
            if head is not None:
                baseline = set(defects(head, path))
                found = [d for d in found if d not in baseline]

        for d in found:
            print(d)
            failed = True
        if not found:
            print(f"{path}: ok ({len(rows) - 1} parts)")

    # The cross-file pass needs every file at once, so it is only meaningful
    # when several are named. Adding a part to one category cannot be judged
    # against the rest of the library from a single file.
    if len(paths) > 1:
        across = cross_defects(current)
        if new_only:
            baseline = set(cross_defects(baseline_rows))
            across = [d for d in across if d not in baseline]
        for d in across:
            print(d)
            failed = True
        if not across:
            print(f"across {len(paths)} files: ok")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
