#!/usr/bin/env python3
"""Check every resistor in a KiCad schematic against the parts database.

For each resistor symbol the script reads the IPN and the resistance the
symbol carries, and asks whether they still agree. Where they do not, it
replaces the IPN with the one that database/g-res.csv gives for that
resistance in the same series.

This verifies rather than translates. It does not need to know what the IPN
used to mean, so it repairs a schematic whatever encoding the number was
written under, and it leaves a correct IPN alone.

Usage:
    update-design-ipns.py <path>...            # report, change nothing
    update-design-ipns.py --write <path>...    # apply the replacements

A path may be a .kicad_sch file or a directory, which is searched for them.
Run with no --write first: the report names every symbol it would touch.

Exits non-zero if any resistor could not be resolved.
"""

import argparse
import csv
import os
import re
import sys

IPN_RE = re.compile(r"^RES-\d{4}-[0-9A-Za-z]{4}$")
DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "database", "g-res.csv")


# --- s-expressions -------------------------------------------------------
#
# The schematic is rewritten by splicing single property values, not by
# reprinting the parsed tree, so every token carries the offsets it came from
# and the rest of the file is preserved byte for byte.

class Token:
    __slots__ = ("value", "start", "end", "quoted")

    def __init__(self, value, start, end, quoted):
        self.value, self.start, self.end, self.quoted = value, start, end, quoted


def parse(text: str):
    """Parse s-expressions into nested lists of Token and list."""
    stack, current, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c == "(":
            stack.append(current)
            current = []
            i += 1
        elif c == ")":
            done, current = current, stack.pop() if stack else []
            current.append(done)
            i += 1
        elif c == '"':
            start, i, chars = i, i + 1, []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    chars.append(text[i + 1])
                    i += 2
                else:
                    chars.append(text[i])
                    i += 1
            i += 1
            current.append(Token("".join(chars), start, i, True))
        else:
            start = i
            while i < n and not text[i].isspace() and text[i] not in "()":
                i += 1
            current.append(Token(text[start:i], start, i, False))
    return current


def head(node) -> str:
    """The name of an s-expression node, or '' for anything else."""
    if isinstance(node, list) and node and isinstance(node[0], Token):
        return node[0].value
    return ""


def properties(symbol):
    """{name: value Token} for a symbol's (property "Name" "Value" ...) children."""
    found = {}
    for child in symbol:
        if head(child) == "property" and len(child) >= 3:
            name, value = child[1], child[2]
            if isinstance(name, Token) and isinstance(value, Token):
                found[name.value] = value
    return found


def symbol_instances(tree):
    """Placed symbols only. Definitions live under lib_symbols and are skipped."""
    for root in tree:
        if head(root) != "kicad_sch":
            continue
        for child in root:
            if head(child) == "symbol":
                yield child


# --- resistance ----------------------------------------------------------

def parse_resistance(text):
    """'4.75K' / '100' / '8.3m' -> ohms. None if unparseable."""
    t = text.strip().replace("Ω", "").replace("ohms", "").replace("ohm", "").strip()
    m = re.fullmatch(r"([\d.]+)\s*([kKmMGR]?)", t)
    if not m:
        return None
    scale = {"": 1.0, "R": 1.0, "K": 1e3, "M": 1e6, "G": 1e9}.get(m.group(2).upper())
    if m.group(2) == "m":
        scale = 1e-3
    if scale is None:
        return None
    try:
        return float(m.group(1)) * scale
    except ValueError:
        return None


def key(ohms: float) -> str:
    """Canonical form so 4.75K and 4750 land on the same database entry."""
    return f"{ohms:.6g}"


def load_database(path):
    """-> ({ipn: ohms}, {(series, value key): ipn})."""
    by_ipn, by_value = {}, {}
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    col = {name.strip(): i for i, name in enumerate(rows[0])}
    for row in rows[1:]:
        if len(row) != len(rows[0]):
            continue
        ipn = row[col["IPN"]].strip()
        ohms = parse_resistance(row[col["Resistance"]])
        if not ipn or ohms is None:
            continue
        by_ipn[ipn] = ohms
        by_value.setdefault((ipn.split("-")[1], key(ohms)), ipn)
    return by_ipn, by_value


# --- the check -----------------------------------------------------------

def find_ipn(props):
    """The IPN field, or any field holding something shaped like a resistor IPN."""
    if "IPN" in props and IPN_RE.match(props["IPN"].value):
        return props["IPN"]
    for name, token in props.items():
        if name != "Reference" and IPN_RE.match(token.value):
            return token
    return None


def check_file(path, by_ipn, by_value, write):
    text = open(path, encoding="utf-8").read()
    tree = parse(text)

    edits, ok, unresolved = [], 0, []
    for symbol in symbol_instances(tree):
        props = properties(symbol)
        token = find_ipn(props)
        if token is None:
            continue
        reference = props["Reference"].value if "Reference" in props else "?"

        stated = None
        for field in ("Resistance", "Value"):
            if field in props:
                stated = parse_resistance(props[field].value)
                if stated is not None:
                    break
        if stated is None:
            unresolved.append(f"{reference}: {token.value} has no readable resistance")
            continue

        # The IPN is right when the database agrees it is this resistance.
        current = by_ipn.get(token.value)
        if current is not None and key(current) == key(stated):
            ok += 1
            continue

        series = token.value.split("-")[1]
        replacement = by_value.get((series, key(stated)))
        if replacement is None:
            unresolved.append(
                f"{reference}: {token.value} states {stated:g} ohm, "
                f"which RES-{series} does not carry"
            )
            continue

        edits.append((token, reference, replacement))

    for token, reference, replacement in edits:
        print(f"  {reference:<6} {token.value} -> {replacement}")
    for problem in unresolved:
        print(f"  {problem}")

    if edits and write:
        for token, _, replacement in sorted(edits, key=lambda e: e[0].start, reverse=True):
            text = text[:token.start] + '"' + replacement + '"' + text[token.end:]
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    return len(edits), ok, len(unresolved)


def schematics(paths):
    for path in paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for name in sorted(files):
                    if name.endswith(".kicad_sch"):
                        yield os.path.join(root, name)
        elif path.endswith(".kicad_sch"):
            yield path
        else:
            print(f"skipping {path}: not a .kicad_sch", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help=".kicad_sch files or directories")
    ap.add_argument("--write", action="store_true", help="apply the replacements")
    ap.add_argument("--parts", default=DEFAULT_DB, help=f"resistor CSV (default {DEFAULT_DB})")
    args = ap.parse_args()

    by_ipn, by_value = load_database(args.parts)

    changed = correct = problems = files = 0
    for path in schematics(args.paths):
        files += 1
        print(f"{path}:")
        c, o, p = check_file(path, by_ipn, by_value, args.write)
        if not (c or p):
            print(f"  {o} resistors, all IPNs agree with their resistance")
        changed, correct, problems = changed + c, correct + o, problems + p

    verb = "updated" if args.write else "to update"
    print(f"\n{files} schematic(s): {correct} already correct, {changed} {verb}, "
          f"{problems} unresolved")
    if changed and not args.write:
        print("Re-run with --write to apply.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
