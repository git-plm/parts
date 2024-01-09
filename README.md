# GitPLM Parts Project

Maintaining eCAD parts libraries is a lot of work. Are you:

- tired of the tedious work of maintaining tradition KiCad libraries or manually
  adding MFG information to each part in a design?
- duplicating symbols in KiCad just because a parameter needs changed?
- duplicating information in your parts database and in schematic symbols?
- duplicating a lot of work in each design and occasionally make mistakes like
  specifying the wrong MPN?
- afraid of of the complexity of setting up a database for KiCad libraries?
- having trouble tracking changes made in a parts database?

The GitPLM Parts project is a collection of best practices that allows you to:

- easily set to a database driven parts libraries without a central database and
  connection (Git friendly).
- leverage a common library of parts across multiple designs.
- easily specify part parameters in table format.
- not duplicate part parameters.
- leverage the standard KiCad symbol library for most common parts.
- easy add variants with just a line in the DB.
- tracks all database changes.

## Using the GitPLM Parts Database in KiCad

Give it a try -- it will only take a few minutes.

- install the following packages: `sqlite3 unixodbc libsqliteodbc sqlitebrowser`
- make sure `/etc/odbcinst.ini` contains a
  [SQLite3 section](https://wiki.archlinux.org/title/Open_Database_Connectivity#SQLite)
- Edit the `parts.kicad_dbl` `connection_string` field to point to the database
  file in this repo. (If anyone knows how to make this path relative, let me
  know.)
- In KiCad Preferences->Manage Symbol Libraries, add the `parts.kicad_dbl` and
  give it a unique Nickname so it is easy to search for.

(above tested on Arch Linux, procedure may vary slightly on other platforms)

Then when you open the symbol chooser, you will see something like:

![image-20240109104709184](./assets/image-20240109104709184.png)

## Update/Generate the database

The following is tested on Linux but should work in any Linux-like command-line
environment.

- edit `csv` files
- if you are adding a new part category, create a new `csv` file, then edit
  `envsetup.sh` to add to the list of imports.
- `. envsetup.sh` (notice the leading `.` -- this is equivalent to the `source`
  command)
- `parts_db_create`
  - this deletes `parts.sqlite` and regenerates it
- `sqlitebrowser` can be used to view/verify the database. Don't edit the
  database as it is overwritten on each import.
- restart KiCad (yes the entire application). This seems to be the only way to
  get KiCad to reload the database changes. (if anyone knows of a better way,
  please let us know!)

## Implementation details

This repo contains a parts database designed to work with
[KiCad Database Libraries feature](https://docs.kicad.org/7.0/en/eeschema/eeschema.html#database-libraries).

The workflow is designed to be _Git Friendly_:

- everything can be checked into Git
- changes can be easily diff'd
- there is no central database that requires network connections, VPNs, etc.

CSV files are a convenient way to store tabular data in Git. Tools like Gitea
are good at
[diffing CSV files](https://community.tmpdir.org/uploads/default/original/2X/2/22193b11a07063ab7759edd6b3cd57a25521073f.png).

So we use the following flow:

`CSV -> Sqlite3 -> ODBC -> KiCad`

This might seem overly complex, but it is actually pretty easy as Sqlite3 can
import `csv` files, so no additional tooling is required. See the
[`envsetup.sh`](envsetup.sh) file for how this is done.

`csv` files can be easily edited in [Libreoffice](https://www.libreoffice.org/).

A separate `csv` file is used for each
[part category](https://github.com/git-plm/gitplm/blob/main/partnumbers.md#three-letter-category-code)
(ex: IND, RES, CAP, etc). There are several reasons for this:

- each part type needs different fields, so this limits the number of columns we
  need in each `csv` file.
- likewise, for each part type, we typically want a different set of fields
  displayed by default in the schematic. The `kicad_dbl` file allows us to
  specify this. For example, with a resistor we want a Resistance field and with
  Capacitors we want a Capacitance field.
- grouping each category into a different library makes it nicer to search for
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

### What to do with the Value field

The `Value` field appears to be special in KiCad and used to identify the part.
Therefore it is suggested to populate the Value field with the `IPN` (Internal
Part Number) so it is unique. The following in the `kicad_dbl` file populates
the Value field in the symbol with the IPN and then hides it.

```
                {
                    "column": "IPN",
                    "name": "Value",
                    "visible_on_add": false,
                    "visible_in_chooser": false,
                    "show_name": false
                },
```

## Status

This is all in the experimental stage. If anyone has better ideas, please let us
know. Issues, PRs, and Discussions are open on this repo. The
[KiCad Forum](https://forum.kicad.info/) or the
[TMPDIR community](https://community.tmpdir.org/) are good places as well.
