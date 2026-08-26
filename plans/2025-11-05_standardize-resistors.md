# Plan: Standardize Resistors

**Date:** 2025-11-05 **Status:** Draft **Task:** Standardize resistor library
with Yageo as preferred manufacturer for standard thick-film 1% resistor series

## Background

The README.md has been updated to document that Yageo is the preferred
manufacturer for standard thick-film 1% resistor series (0402, 0603, etc.) with
all E96 values populated. However, the current resistor database
(`database/g-res.csv`) contains a mix of manufacturers including:

- Vishay/Dale
- Stackpole Electronics
- Bourns
- Panasonic Electronic Components
- Uniroyal
- KOA Speer Electronics
- Yageo (only a few entries)

The resistor library needs to be standardized to align with the documented
policy.

## Current State Analysis

From reviewing `database/g-res.csv` (117 lines total):

### Current Resistor Series Structure

- **RES-0000-xxxx**: 0603 package resistors (various manufacturers: Vishay,
  Stackpole, Bourns, Panasonic, Uniroyal, KOA Speer)
- **RES-0001-xxxx**: 0402 package resistors (primarily Panasonic, KOA Speer)
- **RES-0002-xxxx**: 0805 package resistors (Susumu, Panasonic)
- **RES-0003-xxxx**: 1206 package resistors (TE Connectivity)
- **RES-0004-xxxx**: 1206 package resistors (Vishay Dale)
- **RES-0005-xxxx**: Thermistors (special purpose)
- **RES-0006-xxxx**: High power 0603 (Rohm)
- **RES-0007-xxxx**: Precision 0.1% resistors (Panasonic)
- **RES-0008-xxxx**: Low resistance 1206 (Vishay Dale)
- **RES-0009-xxxx**: 1210 package (Rohm)
- **RES-0010-xxxx**: 0201 package (Yageo)
- **RES-0011-xxxx**: 0201 precision (Vishay Dale)

### Observations

1. Only **RES-0010** series currently uses Yageo
2. The most common packages (0603, 0402) use various manufacturers
3. The existing entries do NOT represent complete E96 series
4. The variation field uses E96 coding (e.g., 1001 = 1kΩ, 1002 = 10kΩ, 1003 =
   100kΩ)
5. Many entries have incomplete specifications (missing voltage or other
   parameters)

## Goals

1. **Standardize on Yageo** for standard 1% thick-film resistor series:

   - 0402 (RES-0001 series)
   - 0603 (RES-0000 series)
   - 0805 (RES-0002 series) if applicable

2. **Populate complete E96 series** for each standard package size

3. **Maintain consistency** with existing part numbering scheme (CCC-NNNN-VVVV
   format)

4. **Preserve special-purpose resistors** that have specific requirements (high
   power, precision, thermistors, etc.)

## Plan of Action

### Phase 1: Research Yageo Part Numbers

1. **Identify Yageo standard resistor series** for each package size:

   - 0402: Find Yageo standard series (likely RC series)
   - 0603: Find Yageo standard series (likely RC series)
   - 0805: Find Yageo standard series (likely RC series)

2. **Verify E96 availability** for each series to ensure all values are
   available

3. **Document Yageo part number format** for each series to enable batch
   generation

### Phase 2: Generate E96 Resistor Lists

Create scripts or tools to:

1. **Generate complete E96 series** for each package size

   - E96 standard values: 1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21,
     1.24, 1.27, 1.30, 1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58, 1.62,
     1.65, 1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15,
     2.21, 2.26, 2.32, 2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87,
     2.94, 3.01, 3.09, 3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83,
     3.92, 4.02, 4.12, 4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11,
     5.23, 5.36, 5.49, 5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65, 6.81,
     6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06, 8.25, 8.45, 8.66, 8.87, 9.09,
     9.31, 9.53, 9.76
   - Across decades: 1Ω to 10MΩ (typical range for 1% resistors)

2. **Map E96 values to E96 4-digit codes** according to the partnumbers.md
   format:

   - Examples: 1000 = 100Ω, 1001 = 1kΩ, 1002 = 10kΩ, 1003 = 100kΩ, 1004 = 1MΩ

3. **Generate Yageo MPNs** for each value based on their part numbering system

### Phase 3: Update Database

1. **Backup existing resistor database**

   - Create a backup of `database/g-res.csv` before making changes

2. **Update RES-0000 series (0603)** to use Yageo parts

   - Replace existing entries with Yageo equivalents
   - Add missing E96 values
   - Preserve special/unique entries that don't have Yageo equivalents

3. **Update RES-0001 series (0402)** to use Yageo parts

   - Replace existing Panasonic entries with Yageo equivalents
   - Add missing E96 values
   - Note: RES-0001-0000 (0Ω jumper) may need special handling

4. **Update RES-0002 series (0805)** if standardizing this package

   - Determine if 0805 should be standardized or kept as-is for special
     applications

5. **Verify special-purpose resistors are preserved:**
   - RES-0005: Thermistors (keep as-is)
   - RES-0006: High power 0603 (keep as-is)
   - RES-0007: Precision 0.1% (keep as-is)
   - RES-0008: Low resistance (keep as-is)
   - RES-0009: High power 1210 (keep as-is)
   - RES-0010: 0201 package (already Yageo)
   - RES-0011: 0201 precision (keep as-is)

### Phase 4: Data Quality & Validation

1. **Ensure data completeness** for all Yageo entries:

   - MPN (Manufacturer Part Number)
   - Manufacturer (Yageo)
   - Description (e.g., "100K 0603")
   - Symbol (Device:R_US)
   - Footprint (correct package size)
   - Resistance (with proper units)
   - Voltage rating
   - Power rating
   - Tolerance (1%)
   - Datasheet URL

2. **Verify IPN uniqueness** - ensure no duplicate IPNs

3. **Verify E96 code consistency** - ensure variation codes properly encode
   resistance values

4. **Sort CSV file by IPN** to maintain consistency and simplify merging

### Phase 5: Update Documentation

1. **Verify README.md** accurately reflects the changes (already has the note
   about Yageo preference)

2. **Update partnumbers.md** if any clarifications are needed about resistor
   encoding

3. **Create migration notes** documenting which parts were changed and why

### Phase 6: Database Regeneration & Testing

1. **Regenerate SQLite database** using `parts_db_create` command

2. **Verify database integrity:**

   - Check that all tables are created correctly
   - Verify row counts match CSV files
   - Spot-check that data imported correctly

3. **Test in KiCad:**
   - Open KiCad and reload the database
   - Search for various resistor values
   - Verify that datasheets and parameters display correctly
   - Test adding resistors to a schematic

## Technical Considerations

### E96 Coding Format

According to `partnumbers.md`, resistor variations use the E96 4-digit format:

- Format: `MMME` where MMM is the mantissa (base value) and E is the exponent
  (multiplier)
- Example: 1001 = 100 × 10¹ = 1000Ω = 1kΩ
- Example: 4751 = 475 × 10¹ = 4750Ω = 4.75kΩ
- Example: 1003 = 100 × 10³ = 100,000Ω = 100kΩ

### Resistance Ranges

Standard 1% resistor ranges typically cover:

- Minimum: 1Ω (or lower for special cases)
- Maximum: 10MΩ (1004 in E96 coding = 100 × 10⁴ = 1,000,000Ω = 1MΩ, so need 1005
  for 10MΩ)

### Yageo Part Number Format

Need to research and document the Yageo part numbering scheme for their RC
series:

- Example: RC0603FR-0710KL (10K 0603 1%)
- Format: RC[package][tolerance]-[power][resistance][packaging]

### CSV Field Mapping

Ensure all fields are populated consistently:

```csv
IPN,MPN,Manufacturer,Description,Symbol,Footprint,Resistance,Voltage,Power,Tolerance,Datasheet
RES-0000-1002,RC0603FR-0710KL,Yageo,10K 0603,Device:R_US,Resistor_SMD:R_0603_1608Metric;R_0603_1608Metric_Pad0.98x0.95mm_HandSolder,10K,75V,100mW,1%,https://www.yageo.com/...
```

## Implementation Steps Summary

1. ☐ Research Yageo part numbers for 0402, 0603, 0805 standard 1% resistor
   series
2. ☐ Create script/tool to generate complete E96 series with proper IPNs and
   MPNs
3. ☐ Backup existing `database/g-res.csv`
4. ☐ Generate new resistor entries for RES-0000 (0603) series with Yageo parts
5. ☐ Generate new resistor entries for RES-0001 (0402) series with Yageo parts
6. ☐ Determine approach for RES-0002 (0805) series
7. ☐ Merge generated entries with existing special-purpose resistors
8. ☐ Validate data completeness and correctness
9. ☐ Sort final CSV by IPN
10. ☐ Run `parts_db_create` to regenerate database
11. ☐ Test in KiCad to verify functionality
12. ☐ Create migration documentation
13. ☐ Commit changes with clear commit message

## Questions to Resolve

1. **Should we replace ALL existing entries or keep backwards compatibility?**

   - Option A: Replace all standard 1% resistors with Yageo equivalents
   - Option B: Keep existing entries and add new Yageo entries alongside them
   - **Recommendation:** Replace to avoid duplication, since IPN scheme allows
     for versions if needed

   Lets go with Option B.

2. **What resistance range should we populate?**

   - Full E96 series from 1Ω to 10MΩ?
   - Or a more limited practical range?
   - **Recommendation:** Start with commonly used range (10Ω to 1MΩ) and expand
     as needed

   Lets go with all values as it is not that many more.

3. **Should we standardize 0805 on Yageo as well?**

   - Current entries use special-purpose parts (low resistance)
   - **Recommendation:** Add new RES-00XX series for standard Yageo 0805 1%
     resistors

   Lets not create additional 0805 resistors at this time, just 0402, and 0603.

4. **How to handle existing designs using old part numbers?**

   - This is a breaking change if MPNs change
   - **Recommendation:** Document the change and provide migration guide;
     designers can update or continue using old entries if preserved

   Not a concern as the database drives everything.

## Success Criteria

1. ✓ All standard 0402 and 0603 1% resistors use Yageo as manufacturer
2. ✓ Complete E96 series populated for standard packages
3. ✓ Special-purpose resistors preserved
4. ✓ Database regenerates without errors
5. ✓ KiCad can successfully load and use the new resistor entries
6. ✓ Documentation updated to reflect changes
7. ✓ All data fields properly populated with complete information

## Risks & Mitigation

| Risk                                   | Impact | Mitigation                                                                        |
| -------------------------------------- | ------ | --------------------------------------------------------------------------------- |
| Yageo doesn't have complete E96 series | High   | Research before starting; identify gaps and document exceptions                   |
| Breaking existing designs              | Medium | Create migration documentation; consider keeping old entries marked as deprecated |
| Incorrect E96 coding                   | High   | Validate codes against standard E96 values; create automated tests                |
| Missing datasheet URLs                 | Low    | Use Yageo's standard datasheet URL pattern; verify availability                   |
| Database import errors                 | Medium | Test import process incrementally; validate CSV format before full import         |

## Timeline Estimate

- Phase 1 (Research): 2-4 hours
- Phase 2 (Generation): 4-6 hours (including script development)
- Phase 3 (Update): 2-3 hours
- Phase 4 (Validation): 2-3 hours
- Phase 5 (Documentation): 1-2 hours
- Phase 6 (Testing): 1-2 hours

**Total: 12-20 hours of work**

## Notes

- This plan focuses on standardization while preserving flexibility for
  special-purpose resistors
- The IPN scheme (RES-NNNN-VVVV) allows for multiple series with different
  characteristics
- E96 variation coding provides a logical, human-readable organization
- Standardizing on Yageo should improve consistency, potentially reduce costs,
  and simplify procurement
