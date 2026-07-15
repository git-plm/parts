# Creating Symbols, Footprints, and 3D Models

Read this only after confirming the KiCad standard library has nothing suitable.
See `SKILL.md` steps 4-6 for the search commands.

## Before authoring: check the vendor first

Many manufacturers publish KiCad symbols and footprints directly, and the
aggregators cover most of the rest:

- The manufacturer's product page (TI, Bourns, Wurth, Molex, and Phoenix Contact
  all publish CAD data)
- SnapEDA / Ultra Librarian / ComponentSearchEngine
- Digi-Key and Mouser product pages link to the above

A vendor-supplied footprint still needs review against the datasheet land
pattern and against the KLC rules below before it goes in. Vendor symbols in
particular tend to violate the pin-length and grid rules.

## Symbols

Custom symbols go in `symbols/g-XXX.kicad_sym`, matching the part's category.
They are then referenced from the CSV as `g-XXX:SymbolName`.

Name the symbol after the part, including the package suffix when the pinout is
package-specific (`LM2903DGK`, not `LM2903`). This is the upstream KiCad
convention and is preferred for new symbols.

Existing symbols in this repo do not follow it consistently - `g-reg.kicad_sym`
alone contains `tps5430`, `TLV709ADJ`, `IC_LT1761-3.3V`, and `MODULE_LTM4638`.
Do not rename them; just do not copy the inconsistency into new work.

### Rules (from README.md and the KiCad KLC)

- Symbol outline stroke width **10 mil** (`0.254` mm)
- Fill with background colour: `(fill (type background))`
- Active-low pins get an overbar via the pin _name_: `~{RESET}`
- Pin length by pin count:
  - fewer than 10 pins: **100 mil** (2.54 mm)
  - 10-99 pins: **150 mil** (3.81 mm)
  - 100+ pins: **200 mil** (5.08 mm)
- **Every pin must land on a 100 mil (2.54 mm) grid**, whatever the pin length.
  This is what makes wires connect reliably in the schematic editor.
- Place the symbol origin on the **lower-leftmost pin**. Consistent origins make
  symbols swappable and keep ERC sane.
- Pin electrical types matter for ERC. Follow the upstream convention:
  `power_in` for supply and ground pins, `power_out` for a switching node or
  regulator output, `input`/`output`/`bidirectional` for signals, `passive` for
  discretes.

The `Value` field is populated from the database, so leave it alone in the
symbol itself. Per the `http.fields` section of `gitplm.yml`, `Value` maps to
the `MPN` column for most categories, and to the value column (`Resistance`,
`Capacitance`, `Inductance`) for passives - Spice reads that field.

### Authoring

The KiCad symbol editor is the practical way to draw a symbol, and it normalizes
formatting on save. When hand-writing the s-expression, copy the surrounding
symbols in the target `.kicad_sym` file for the exact format version and
indentation (tabs).

Render it to check the result:

```bash
kicad-cli sym export svg --symbol <SymbolName> -o /tmp/sym symbols/g-reg.kicad_sym
```

## Footprints

Custom footprints go in `footprints/g-XXX.pretty/<Name>.kicad_mod`. Name them
`<Manufacturer>_<Series>` (`Bourns_SRP6540`, `Coilcraft_DO1608C`) to match the
existing files.

Build the pads from the datasheet's **recommended land pattern**, not from the
package body dimensions. Read that drawing from the PDF pages directly (see
SKILL.md step 1) - never from a text summary, which will invent dimensions.

Land pattern drawings often give only a few figures (inner gap, overall span,
pad height). Derive pad size and centres arithmetically from those, and state in
your report which numbers were given and which you derived.

### Origin rule

- **Surface mount**: origin in the dead centre of the part. Pick-and-place
  machines are programmed from this.
- **Through hole**: origin on pin 1. These are placed by hand and usually
  dimensioned against enclosure features and mating boards.

### Other conventions

- `(attr smd)` or `(attr through_hole)`
- Silkscreen must not overlap exposed copper. When pads extend past the body,
  draw only the body edges that clear them.
- Courtyard on `F.CrtYd` at 0.05 mm stroke.
- Pin 1 marker on silkscreen and fab layers for anything polarized. Omit it for
  symmetric two-terminal parts.

Render it to check:

```bash
kicad-cli fp export svg --footprint <Name> -o /tmp/fp footprints/g-ind.pretty
```

## 3D models

### Standard footprints

Nothing to author. The footprint already contains a
`(model "${KICAD10_3DMODEL_DIR}/<Lib>.3dshapes/<Name>.step" ...)` block, and the
STEP file usually ships with `kicad-library-3d`. Usually, not always - some
footprints reference a `.step` the installed package omits (e.g.
`TQFN-32-1EP_5x5mm_P0.5mm_EP3.4x3.4mm` in `kicad-library-3d 10.0.4`: reference
present, file absent). That is an upstream packaging gap affecting every user of
the footprint, not something to fix here and not a reason to reject the
footprint - just confirm with `ls .../<Lib>.3dshapes/<Name>.step` when it
matters and tell the user if it is missing.

The version in that variable tracks the installed KiCad (currently 10). Custom
footprints in this repo still carry `KICAD6_3DMODEL_DIR` and
`KICAD8_3DMODEL_DIR` from when they were authored; KiCad resolves the older
names, so leave them alone. New custom footprints should use
`${GITPLM_3DMODELS}` anyway, which is version-independent.

### Custom footprints

3D models are **not stored in this repo**. They live in a separate repository,
which KiCad locates through the `GITPLM_3DMODELS` environment variable (set in
KiCad under Preferences -> Configure Paths, not by `envsetup.sh`).

On this machine it is already cloned alongside the parts repo:

```bash
ls ../3d-models          # remote: git@git.bec-systems.com:GitPLM/3d-models.git
```

Check for it before cloning anything - the public `github.com/git-plm/3d-models`
is a different, upstream copy. Confirm the path `GITPLM_3DMODELS` actually
points at:

```bash
grep -r GITPLM_3DMODELS ~/.config/kicad/*/kicad_common.json
```

Steps:

1. **Find a STEP file.** In descending order of preference: the manufacturer's
   product page, then Ultra Librarian / SnapEDA / ComponentSearchEngine, then
   3DContentCentral or GrabCAD. STEP (`.step`, `.stp`) is preferred over WRL -
   it is what the rest of the library uses and it exports to mechanical CAD. A
   sibling variant's model is usually geometrically identical and safe to reuse
   when the exact MPN has none.
2. **Commit it to the 3d-models repo**, not this one. Name the file after the
   MPN or series (`SRP6540.step`), matching the flat naming already used there.
3. **Reference it from the footprint** with the environment variable:
   ```
   (model "${GITPLM_3DMODELS}/SRP6540.step"
       (offset (xyz 0 0 0))
       (scale (xyz 1 1 1))
       (rotate (xyz 0 0 0))
   )
   ```
4. **Verify alignment in the KiCad 3D viewer.** Vendor STEP files often place
   the origin at a corner or at the bottom of the body rather than at the
   footprint origin, and are frequently rotated. Correct with `offset` and
   `rotate` rather than editing the STEP.
   `footprints/g-ind.pretty/Wurth744062003.kicad_mod` uses a Z offset for
   exactly this reason - read it as a worked example.

If no 3D model can be found, the footprint is still valid without a `model`
block. Say so explicitly rather than leaving the user to discover it.
