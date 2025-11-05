# GitPLM Parts Project

<!--toc:start-->

- [GitPLM Parts Project](#gitplm-parts-project)
  - [Overview](#overview)
  - [Demo Video](#demo-video)
  - [Using the GitPLM Parts Database in KiCad](#using-the-gitplm-parts-database-in-kicad)
  - [Update/Generate the database](#updategenerate-the-database)
  - [Debugging broken `*.kicad_dbl` files](#debugging-broken-kicaddbl-files)
  - [Adding New Parts](#adding-new-parts)
  - [Implementation details](#implementation-details)
  - [Directories](#directories)
  - [Status/Support](#statussupport)
  - [Reference](#reference)
  <!--toc:end-->

(See also our [document on partnumber formats](partnumbers.md).)

## Overview

**Maintaining eCAD parts libraries is a lot of work. Are you:**

- Tired of the tedious work of maintaining tradition KiCad libraries or manually
  adding MFG information to each part in a design?
- Duplicating symbols in KiCad just because a parameter needs changed?
- Duplicating information in your parts database and in schematic symbols?
- Duplicating a lot of work in each design and occasionally make mistakes like
  specifying the wrong MPN?
- Afraid of the complexity of setting up a database for KiCad libraries?
- Are you having trouble tracking who made what changes made in a parts
  database?
- Struggling to find a CAD library process that will scale to large teams?

**The GitPLM Parts project is a collection of best practices that allows you
to:**

1. Easily set to a database driven parts libraries without a central database
   and connection (Git friendly).
2. Leverage a common library of parts across multiple designs.
3. Easily specify part parameters in table format.
4. Not duplicate part parameters.
5. Leverage the standard KiCad symbol library for most common parts.
6. Easy add variants with just a line in a CSV file.
7. Track all database changes.
8. Scale to multiple designers.

## Demo Video

Click the image below to see a demonstration of this library in use:

[https://youtu.be/uXw8gY1IN_A](https://youtu.be/uXw8gY1IN_A)

[![watch video](https://img.youtube.com/vi/uXw8gY1IN_A/maxresdefault.jpg)](https://youtu.be/uXw8gY1IN_A)

## Using the GitPLM Parts Database in KiCad

Give it a try - it will only take a few minutes.

- Clone this repo: `git clone https://github.com/git-plm/parts.git`
- Clone the 3d models repo: `git clone https://github.com/git-plm/3d-models.git`
- In KiCad Preferences->Configure Paths:
  - set `GITPLM_PARTS` to the location of the parts repo
  - set `'GITPLM_3DMODELS` to the location of the 3d-models repo
- Install the following packages: `sqlite3 unixodbc libsqliteodbc`
  - Arch Linux has the `sqliteodbc` package in the Arch AUR
- Optionally install the following packages:
  `sqlitebrowser visidata inotify-tools`
- Make sure `/etc/odbcinst.ini` contains a
  [SQLite3 section](https://wiki.archlinux.org/title/Open_Database_Connectivity#SQLite)
- In KiCad Preferences->Manage Symbol Libraries:
  - Add all the libraries in the `symbols` directory
  - Add the `database/#gplm.kicad_dbl`. This filename is prefixed with `#` so
    that it shows up at the top of the list in the schematic symbol chooser.
- In KiCad Preferences->Manage Footprint Libraries:
  - Add all `g-*.pretty` directories in the `footprints` directory

(above tested on Arch Linux, so the bits about SQLite3 libraries may vary
slightly on other platforms). Also tested on Ubuntu 23.04, use the same
instructions as for Arch Linux (apt install `sqlite3` `unixodbc` etc. ...)

Then when you open the symbol chooser, you will see something like:

![image-20240304103012907](./assets/image-20240304103012907.png)

Notes, the `#gplm` entries are at the top where they are quick to get to.

Right-clicking on the column headings in the chooser allows you to specify which
parameters are displayed.

## Update/Generate the database

The following is tested on Linux but should work in any Linux-like command-line
environment.

- Edit `csv` files
- If you are adding a new part category, create a new `csv` file, then edit
  `envsetup.sh` to add to the list of imports.
- `. envsetup.sh` (notice the leading `.` - this is equivalent to the `source`
  command)
- Run the `parts_db_create` command
  - this deletes `parts.sqlite` and regenerates it
- `sqlitebrowser` can be used to view/verify the database. Don't edit the
  database as it is overwritten on each import.
- **Restart KiCad** (yes the entire application). This seems to be the only way
  to get KiCad to reload the database changes. (if anyone knows of a better way,
  please let us know!)

## Debugging broken `*.kicad_dbl` files

Sometimes when you modify the `#gplm.kicad_dbl` file, there is a typo and KiCad
will no longer load it and does not give you any helpful debugging messages. You
can use the [`jq`](https://github.com/jqlang/jq) command line utility to quickly
find errors in the file, since the `kicad_dbl` format appears to be JSON.

`jq . \#gplm.kicad_dbl`

## Adding New Parts

If the symbol and footprint already exist, adding a new part is simple as:

1. Add a line to one of the `csv` files. The `csv` files should be sorted by
   `IPN`. This ensures the `IPN` is unique (which is the lib/db key), and merge
   operations are simpler if the file is always sorted.
2. run `parts_db_create`
3. restart KiCad

If you need to add a symbol or footprint, add to the matching `g-XXX.kicad_sym`,
or `g-XXX.pretty` libraries. Standards in the
[KiCad KLC](https://klc.kicad.org/) should be followed as much as possible.
Specific requirements:

1. Set symbol outline to 10mil
2. Fill symbol with background color (light yellow)
3. Active low pins should be designated using a bar. This is done with the
   following pin name syntax: `~{PIN_NAME}`
4. symbol pin lengths
   - \< 10 pins: 100mil
   - 10 - 99 pins: 150mil
   - \> 100 pins: 200mil

NOTE: To aid in the accurate connection of wires in EESCHEMA symbol pins,
regardless of their pin lengths, should fall on a 100mil/2.54mm grid. Move the
symbol so its origin falls on the lower leftmost pin of the symbol. Having
consistent symbol origins facilitates moving and updating or replacing symbols
during the editing process and makes ERC checking easier.

For footprints the symbol origin for surface mounted parts should be placed in
the dead center of the part to aid in programming automated assembly machines.
For through hole parts, that are not automatically placed, usually pin 1 serves
as the origin to simplify dimensioning since components such as connectors often
have placement restrictions necessitated by other features such as openings in
enclosures, mating PCB's, and so on.

The KiCad symbol `Value` field is populated with:

- Resistance, capacitance, and inductance for passives. Spice simulations use
  the value field, so it is good to have it populated.
- MPN for most other parts

### Preferred manufacturers

- Yageo is the preferred manufacturer for standard thick-film 1% `0402` `0603`
  etc. resistor series (`RES-0000`, `RES-0001`). All `E96` values are populated
  for these series.

## Implementation details

This repo contains a parts database designed to work with
[KiCad Database Libraries feature](https://docs.kicad.org/7.0/en/eeschema/eeschema.html#database-libraries).

The IPN (Internal Part Number) format used is specified in
[this document](partnumbers.md).

IPN format: `CCC-NNNN-VVVV`

- `CCC`: one to three letters or numbers to identify major category (`RES`,
  `CAP`, `DIO`, etc.).
- `NNNN`: incrementing sequential number for each part. This gives this format
  flexibility.
- `VVVV`: use to code variations of similar parts typically with the same
  datasheet or family (resistance, capacitance, regulator voltage, IC package,
  screw type, etc.). `VVVV` is also used to encode version and variations for
  manufactured parts or assemblies.

The workflow is designed to be _Git Friendly_:

- Everything can be checked into Git
- Changes can be easily diff'd
- There is no central database that requires network connections, VPNs, etc.
- All changes to the parts database are tracked in Git.

CSV files are a convenient way to store tabular data in Git. Tools like Gitea
and GitHub are good at
[viewing](https://github.com/git-plm/parts/blob/main/cap.csv) and
[diffing CSV files](https://community.tmpdir.org/uploads/default/original/2X/2/22193b11a07063ab7759edd6b3cd57a25521073f.png).
This allows anyone to edit the database. Complex database permissions are not
required as workflow is managed through standard Git mechanisms like PRs. As an
example, changes from new users may be reviewed before merging to the main
branch.

So we use the following flow:

`CSV -> Sqlite3 -> ODBC -> KiCad`

This might seem overly complex, but it is actually pretty easy as SQLite3 can
import `csv` files, so no additional tooling is required. See the
[`envsetup.sh`](envsetup.sh) file for how this is done.

`csv` files can be easily edited in [LibreOffice](https://www.libreoffice.org/)
or [VisiData](https://www.visidata.org/). **Note, in LibreOffice make sure you
import CSV files with character set as `UTF-8` (`UTF-7`, which seems to be the
default, will cause bad things to happen)**

If you use VisiData on Linux, please set the following option in `~/.visidatarc`
to make the CSV line endings compatible with LibreOffice Calc:

```
options.csv_lineterminator = "\x0a"
```

A separate `csv` file is used for each
[part category](https://github.com/git-plm/gitplm/blob/main/partnumbers.md#three-letter-category-code)
(ex: `IND`, `RES`, `CAP`, etc.). There are several reasons for this:

- Each part type needs different fields, so this limits the number of columns we
  need in each `csv` file.
- Likewise, for each part type, we typically want a different set of fields
  displayed by default in the schematic. The `kicad_dbl` file allows us to
  specify this. For example, with a resistor we want a Resistance field and with
  Capacitors we want a Capacitance field.
- Grouping each category into a different library makes it nicer to search for
  parts.

This database is designed to be general purpose and can be used by multiple
projects and companies. Practically, things vary a lot between different
companies so this will likely serve more as an example.

Initially, this part database will be optimized for low-cost rapid prototyping
at places like [JLCPCB](https://jlcpcb.com/) and
[Seeed Studio](https://www.seeedstudio.com/fusion_pcb.html) using parts from:

- https://jlcpcb.com/Parts
- https://www.seeedstudio.com/opl.html

(this may not be work out so the approach may change)

## Directories

- `database` - CSV files and the SQLite3 database file
- `symbols` - custom KiCad symbols
- `footprints` - custom KiCad footprints
- `spice` - spice models
- `libs` - contains the KiCad standard library symbols/footprints. This is added
  as a submodule here for convenience as a quick way to check out the KiCad
  standard libraries in case you want to modify them.

## Status/Support

This library is currently being used successfully in several projects. We
currently do most work in an Internal Gitea repo as the CSV diff functionality
is so much better than GitHub, but periodically push updates to this mirror.

For commercial support, training, or design assistance, please contact us at:

- [TMPDIR community](https://community.tmpdir.org/)
- [BEC Systems](https://bec-systems.com/)

## Reference

- https://forum.kicad.info/t/gitplm-parts-kicad-database-ideas/47358
- https://docs.kicad.org/7.0/en/eeschema/eeschema.html#database-libraries
- https://forum.kicad.info/t/kicad-the-case-for-database-driven-design/34621
- https://wiki.archlinux.org/title/Open_Database_Connectivity
