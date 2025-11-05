#!/usr/bin/env python3
"""
Merge generated Yageo resistors with existing special-purpose resistors.

This script:
1. Reads the existing g-res.csv
2. Identifies special-purpose resistors (series > 0001)
3. Reads generated Yageo 0603 and 0402 resistors
4. Combines them into a new g-res.csv
5. Sorts by IPN
"""

import csv
from typing import List, Dict


def read_csv(filename: str) -> List[Dict]:
    """Read CSV file and return list of dictionaries."""
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(filename: str, data: List[Dict], fieldnames: List[str]):
    """Write list of dictionaries to CSV file."""
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def extract_series_number(ipn: str) -> int:
    """Extract series number from IPN (e.g., 'RES-0005-1002' -> 5)."""
    parts = ipn.split('-')
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            return 0
    return 0


def main():
    """Main merge function."""
    print("Reading existing g-res.csv...")
    existing_resistors = read_csv('/scratch/bec/parts/database/g-res.csv')

    print(f"Found {len(existing_resistors)} existing resistors")

    # Separate special-purpose resistors (series >= 0002)
    # According to plan: keep series 0002-0011 as special purpose
    # Replace series 0000 (0603) and 0001 (0402) with Yageo parts
    special_purpose = []
    old_standard = []

    for resistor in existing_resistors:
        series_num = extract_series_number(resistor['IPN'])
        if series_num >= 2:
            special_purpose.append(resistor)
            print(f"  Keeping special-purpose: {resistor['IPN']} - {resistor['Description']}")
        else:
            old_standard.append(resistor)

    print(f"\nSpecial-purpose resistors to keep: {len(special_purpose)}")
    print(f"Standard resistors to replace: {len(old_standard)}")

    # Read generated Yageo resistors
    print("\nReading generated Yageo 0603 resistors...")
    yageo_0603 = read_csv('/scratch/bec/parts/database/generated-res-0603.csv')
    print(f"Found {len(yageo_0603)} Yageo 0603 resistors")

    print("\nReading generated Yageo 0402 resistors...")
    yageo_0402 = read_csv('/scratch/bec/parts/database/generated-res-0402.csv')
    print(f"Found {len(yageo_0402)} Yageo 0402 resistors")

    # Combine all resistors
    all_resistors = yageo_0603 + yageo_0402 + special_purpose

    print(f"\nTotal resistors: {len(all_resistors)}")
    print(f"  Yageo 0603: {len(yageo_0603)}")
    print(f"  Yageo 0402: {len(yageo_0402)}")
    print(f"  Special purpose: {len(special_purpose)}")

    # Sort by IPN
    print("\nSorting by IPN...")
    all_resistors.sort(key=lambda x: x['IPN'])

    # Write merged CSV
    output_file = '/scratch/bec/parts/database/g-res.csv'
    print(f"\nWriting merged resistors to {output_file}...")

    fieldnames = ['IPN', 'MPN', 'Manufacturer', 'Description', 'Symbol',
                 'Footprint', 'Resistance', 'Voltage', 'Power', 'Tolerance', 'Datasheet']

    write_csv(output_file, all_resistors, fieldnames)

    print(f"\nMerge complete! Total entries: {len(all_resistors)}")

    # Print summary by series
    print("\nSummary by series:")
    series_count = {}
    for resistor in all_resistors:
        series_num = extract_series_number(resistor['IPN'])
        series_count[series_num] = series_count.get(series_num, 0) + 1

    for series_num in sorted(series_count.keys()):
        print(f"  RES-{series_num:04d}: {series_count[series_num]} parts")


if __name__ == "__main__":
    main()
