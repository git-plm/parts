#!/usr/bin/env python3
"""Check every resistor in a KiCad design against the parts database.

For each resistor the script reads the IPN and the resistance the part
carries, and asks whether they still agree. Where they do not, it replaces
the IPN with the one that database/g-res.csv gives for that resistance in
the same series.

An IPN is named in more than one place, and all of them have to move
together. A schematic names it in the placed symbol's IPN field, in that
symbol's lib_id, and three more times in the lib_symbols cache: as the
definition name, in the definition's own IPN field, and in the name of each
sub-unit. A board names it in the footprint's IPN field. Updating only the
placed symbol's field leaves the rest pointing at the old part, and a later
"Update Symbols from Library" pulls the old number back.

This verifies rather than translates. It does not need to know what the IPN
used to mean, so it repairs a design whatever encoding the number was
written under, and it leaves a correct IPN alone.

Usage:
    update-design-ipns.py <path>...            # report, change nothing
    update-design-ipns.py --write <path>...    # apply the replacements

A path may be a .kicad_sch or .kicad_pcb file, or a directory, which is
searched for them. Run with no --write first: the report names every part it
would touch.

Exits non-zero if any resistor could not be resolved.
"""

import argparse
import csv
import os
import re
import sys

IPN_RE = re.compile(r"^RES-\d{4}-[0-9A-Za-z]{4}$")
SUBUNIT_RE = re.compile(r"_\d+_\d+$")
DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "database", "g-res.csv")


# --- s-expressions -------------------------------------------------------
#
# The design is rewritten by splicing single tokens, not by reprinting the
# parsed tree, so every token carries the offsets it came from and the rest
# of the file is preserved byte for byte.

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


def render(token: Token, value: str) -> str:
    """The literal text that puts `value` where `token` was."""
    if not token.quoted:
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def properties(node):
    """{name: value Token} for a node's (property "Name" "Value" ...) children."""
    found = {}
    for child in node:
        if head(child) == "property" and len(child) >= 3:
            name, value = child[1], child[2]
            if isinstance(name, Token) and isinstance(value, Token):
                found[name.value] = value
    return found


def part_nodes(tree):
    """Every symbol or footprint node, at any depth.

    Unlike a placement-only walk this reaches into lib_symbols. Those cached
    definitions carry the same IPN and resistance as the symbols placed from
    them, and they go stale in exactly the same way.
    """
    def walk(node):
        if not isinstance(node, list):
            return
        if head(node) in ("symbol", "footprint"):
            yield node
        for child in node:
            yield from walk(child)

    for root in tree:
        yield from walk(root)


def definition_name(node):
    """The library name a lib_symbols definition declares, else None.

    A definition is (symbol "#gplm:RES-0000-8251" ...); a placed symbol is
    (symbol (lib_id ...) ...), whose second element is a list, not a name.
    """
    if head(node) != "symbol" or len(node) < 2:
        return None
    name = node[1]
    if isinstance(name, Token) and name.quoted:
        return name.value
    return None


# --- IPN references ------------------------------------------------------

def referenced_ipn(value: str):
    """The IPN a token names, or None.

    Covers the bare field value (RES-0000-8251), the library-qualified name
    used by lib_id and by the definition (#gplm:RES-0000-8251), and the
    sub-unit names inside a definition (RES-0000-8251_0_1).
    """
    base = value.split(":", 1)[1] if ":" in value else value
    base = SUBUNIT_RE.sub("", base)
    return base if IPN_RE.match(base) else None


def rewrite_reference(value: str, ipn: str) -> str:
    """`value` with its IPN swapped for `ipn`, keeping prefix and suffix."""
    prefix = value.split(":", 1)[0] + ":" if ":" in value else ""
    suffix = SUBUNIT_RE.search(value)
    return prefix + ipn + (suffix.group(0) if suffix else "")


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


def describe(node, props):
    """How a part is named in the report."""
    definition = definition_name(node)
    if definition:
        return f"lib {definition}"
    return props["Reference"].value if "Reference" in props else "?"


def decide(tree, by_ipn, by_value):
    """-> (renames, ok count, per-part problems, file-level blockers)."""
    proposed, ok, unresolved = {}, 0, []

    for node in part_nodes(tree):
        props = properties(node)
        token = find_ipn(props)
        if token is None:
            continue
        name = describe(node, props)

        stated = None
        for field in ("Resistance", "Value"):
            if field in props:
                stated = parse_resistance(props[field].value)
                if stated is not None:
                    break
        if stated is None:
            unresolved.append(f"{name}: {token.value} has no readable resistance")
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
                f"{name}: {token.value} states {stated:g} ohm, "
                f"which RES-{series} does not carry"
            )
            continue

        proposed.setdefault(token.value, {}).setdefault(replacement, []).append(name)

    # One old IPN becomes one new IPN. Where the design disagrees with itself
    # the rename is ambiguous, and renaming the shared library definition
    # would be wrong for one of the parts either way.
    renames, blockers = {}, []
    for old, candidates in sorted(proposed.items()):
        if len(candidates) > 1:
            detail = "; ".join(f"{new} for {', '.join(names)}"
                               for new, names in sorted(candidates.items()))
            blockers.append(f"{old} would have to become more than one part: {detail}")
            continue
        renames[old] = next(iter(candidates))

    # Two definitions under one name would leave KiCad to pick between them.
    definitions = {}
    for node in part_nodes(tree):
        name = definition_name(node)
        if not name or SUBUNIT_RE.search(name):
            continue
        old = referenced_ipn(name)
        if old:
            definitions.setdefault(renames.get(old, old), set()).add(old)
    for new, sources in sorted(definitions.items()):
        if len(sources) > 1:
            blockers.append(
                f"{' and '.join(sorted(sources))} would both become {new}, "
                f"leaving two library definitions under one name"
            )

    if blockers:
        renames = {}
    return renames, ok, unresolved, blockers


def collect_edits(tree, renames):
    """Every token in the file that names a renamed IPN, in any of its forms."""
    edits = []

    def walk(node):
        if isinstance(node, Token):
            old = referenced_ipn(node.value)
            if old in renames:
                new_value = rewrite_reference(node.value, renames[old])
                if new_value != node.value:
                    edits.append((node, old, new_value))
            return
        for child in node:
            walk(child)

    for root in tree:
        walk(root)
    return edits


def check_file(path, by_ipn, by_value, write):
    text = open(path, encoding="utf-8").read()
    tree = parse(text)

    renames, ok, unresolved, blockers = decide(tree, by_ipn, by_value)
    edits = collect_edits(tree, renames)

    parts = {}
    for node in part_nodes(tree):
        props = properties(node)
        token = find_ipn(props)
        if token is not None and token.value in renames:
            parts.setdefault(token.value, []).append(describe(node, props))

    for old, new in sorted(renames.items()):
        named = parts.get(old, [])
        refs = sum(1 for _, o, _ in edits if o == old)
        print(f"  {old} -> {new}  ({len(named)} parts, {refs} references)")
        if named:
            print(f"      {', '.join(named)}")
    for problem in unresolved:
        print(f"  {problem}")
    for problem in blockers:
        print(f"  cannot rewrite this file: {problem}")

    if edits and write:
        for token, _, new_value in sorted(edits, key=lambda e: e[0].start, reverse=True):
            text = text[:token.start] + render(token, new_value) + text[token.end:]
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    return len(renames), len(edits), ok, len(unresolved) + len(blockers)


def designs(paths):
    """The .kicad_sch and .kicad_pcb files under the given paths.

    Editor history, KiCad's own backups, and autosaves are not design inputs,
    so directory walks skip them. An explicitly named file is always used.
    """
    def skip(name):
        return name in (".git", ".history") or name.endswith("-backups")

    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not skip(d)]
                for name in sorted(files):
                    if name.startswith("_autosave-"):
                        continue
                    if name.endswith((".kicad_sch", ".kicad_pcb")):
                        yield os.path.join(root, name)
        elif path.endswith((".kicad_sch", ".kicad_pcb")):
            yield path
        else:
            print(f"skipping {path}: not a .kicad_sch or .kicad_pcb", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help=".kicad_sch / .kicad_pcb files or directories")
    ap.add_argument("--write", action="store_true", help="apply the replacements")
    ap.add_argument("--parts", default=DEFAULT_DB, help=f"resistor CSV (default {DEFAULT_DB})")
    args = ap.parse_args()

    by_ipn, by_value = load_database(args.parts)

    changed = references = correct = problems = files = 0
    for path in designs(args.paths):
        files += 1
        print(f"{path}:")
        c, r, o, p = check_file(path, by_ipn, by_value, args.write)
        if not (c or p):
            print(f"  {o} resistors, all IPNs agree with their resistance")
        changed, references = changed + c, references + r
        correct, problems = correct + o, problems + p

    verb = "updated" if args.write else "to update"
    print(f"\n{files} file(s): {correct} resistor fields already correct, "
          f"{changed} IPNs {verb} across {references} references, {problems} unresolved")
    if changed and not args.write:
        print("Re-run with --write to apply.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
