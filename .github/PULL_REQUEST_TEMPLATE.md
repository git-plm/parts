## What this changes

<!-- One or two sentences. If parts were added, name the MPNs and the IPNs they
were given. -->

## Checklist

- [ ] `scripts/check-csv.py --new-only database/g-*.csv` reports `ok`
- [ ] Every spec came from the manufacturer's datasheet, and the `Datasheet`
      column links to it over https
- [ ] New rows are inserted in IPN sorted position, not appended
- [ ] No new part number reuses a retired one, and a superseded part keeps its
      row with `Replaced by <IPN>` in `Status`
- [ ] `Symbol` and `Footprint` resolve in KiCad, and the part places and renders
      as expected
- [ ] Markdown is formatted: `. envsetup.sh && parts_format_check`
- [ ] Only the files this change needs are staged; 3D models live in the
      separate [3d-models](https://github.com/git-plm/3d-models) repo

## Notes for the reviewer

<!-- Anything worth a second look: a new series, an authored symbol or
footprint, a convention this change sets. Delete if there is nothing. -->
