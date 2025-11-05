#!/usr/bin/env python3
"""
Generate Yageo E96 resistor series for 0402 and 0603 packages.
This script generates CSV entries for the complete E96 series from 1Ω to 10MΩ.
"""

import csv
from typing import List, Tuple

# E96 series base values (1% tolerance)
E96_VALUES = [
    1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24,
    1.27, 1.30, 1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58,
    1.62, 1.65, 1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00,
    2.05, 2.10, 2.15, 2.21, 2.26, 2.32, 2.37, 2.43, 2.49, 2.55,
    2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09, 3.16, 3.24,
    3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
    4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23,
    5.36, 5.49, 5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65,
    6.81, 6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06, 8.25, 8.45,
    8.66, 8.87, 9.09, 9.31, 9.53, 9.76
]

# Decades to generate (exponents)
# 10^0 = 1Ω to 10^6 = 1MΩ (then one more decade to 10MΩ)
DECADES = [0, 1, 2, 3, 4, 5, 6]  # 1Ω to 10MΩ


def resistance_to_e96_code(resistance_ohms: float) -> str:
    """
    Convert resistance in ohms to E96 4-digit code (MMME format).

    The format is: MMM E where MMM is the mantissa (100-999) and E is the exponent (0-6).
    Examples:
      - 100Ω = 100 × 10^0 = 1000
      - 1kΩ = 100 × 10^1 = 1001
      - 10kΩ = 100 × 10^2 = 1002
      - 4.75kΩ = 475 × 10^1 = 4751

    Args:
        resistance_ohms: Resistance value in ohms

    Returns:
        E96 code string (e.g., "1001" for 1kΩ)
    """
    if resistance_ohms == 0:
        return "0000"

    # Handle sub-ohm resistances with special encoding
    if resistance_ohms < 1:
        # For values < 1Ω, use special format like "R100" for 0.1Ω
        # This is used for miliohm resistors
        if resistance_ohms >= 0.1:
            code = f"R{int(resistance_ohms * 10):02d}0"[:4]
        else:
            code = f"0{int(resistance_ohms * 100):02d}m"[:4]
        return code

    # Find the exponent (how many decades above 1Ω)
    import math
    exponent = int(math.floor(math.log10(resistance_ohms)))

    # Calculate mantissa
    mantissa = resistance_ohms / (10 ** exponent)

    # Scale mantissa to be between 100-999
    mantissa = round(mantissa * 100)

    # Adjust if mantissa rounds to 1000
    if mantissa >= 1000:
        mantissa = 100
        exponent += 1

    # Ensure mantissa is in valid range
    if mantissa < 100:
        mantissa = 100

    # Create 4-digit code
    code = f"{mantissa:03d}{exponent}"
    return code


def format_resistance_value(resistance_ohms: float) -> str:
    """
    Format resistance value for display in Description field.

    Args:
        resistance_ohms: Resistance value in ohms

    Returns:
        Formatted string (e.g., "10K", "100", "1.5K")
    """
    if resistance_ohms == 0:
        return "0"
    elif resistance_ohms < 1:
        return f"{resistance_ohms}R"
    elif resistance_ohms < 1000:
        # Format as ohms
        if resistance_ohms == int(resistance_ohms):
            return f"{int(resistance_ohms)}"
        else:
            return f"{resistance_ohms:.2f}".rstrip('0').rstrip('.')
    elif resistance_ohms < 1000000:
        # Format as K
        k_value = resistance_ohms / 1000
        if k_value == int(k_value):
            return f"{int(k_value)}K"
        else:
            return f"{k_value:.2f}".rstrip('0').rstrip('.') + "K"
    else:
        # Format as M
        m_value = resistance_ohms / 1000000
        if m_value == int(m_value):
            return f"{int(m_value)}M"
        else:
            return f"{m_value:.2f}".rstrip('0').rstrip('.') + "M"


def format_yageo_mpn_value(resistance_ohms: float) -> str:
    """
    Format resistance value for Yageo MPN encoding.

    Args:
        resistance_ohms: Resistance value in ohms

    Returns:
        Yageo resistance encoding (e.g., "10KL", "100RL", "1K5L")
    """
    if resistance_ohms == 0:
        return "0RL"
    elif resistance_ohms < 1:
        # Sub-ohm: use R as decimal point (e.g., 0.1Ω = "R10L")
        return f"R{int(resistance_ohms * 10)}L"
    elif resistance_ohms < 1000:
        # Ohms: append R (e.g., 10Ω = "10RL")
        if resistance_ohms == int(resistance_ohms):
            return f"{int(resistance_ohms)}RL"
        else:
            # Use R as decimal point (e.g., 1.5Ω = "1R5L")
            str_val = f"{resistance_ohms:.2f}".rstrip('0').rstrip('.')
            if '.' in str_val:
                return str_val.replace('.', 'R') + "L"
            return str_val + "RL"
    elif resistance_ohms < 1000000:
        # kΩ: append KL
        k_value = resistance_ohms / 1000
        if k_value == int(k_value):
            return f"{int(k_value)}KL"
        else:
            # Use K as decimal point for fractional values (e.g., 1.5kΩ = "1K5L")
            str_val = f"{k_value:.2f}".rstrip('0').rstrip('.')
            if '.' in str_val:
                return str_val.replace('.', 'K') + "L"
            return str_val + "KL"
    else:
        # MΩ: append ML
        m_value = resistance_ohms / 1000000
        if m_value == int(m_value):
            return f"{int(m_value)}ML"
        else:
            str_val = f"{m_value:.2f}".rstrip('0').rstrip('.')
            if '.' in str_val:
                return str_val.replace('.', 'M') + "L"
            return str_val + "ML"


def generate_yageo_mpn(package: str, resistance_ohms: float) -> str:
    """
    Generate Yageo MPN for given package and resistance.

    Format: RC[package]FR-07[resistance]
    Example: RC0603FR-0710KL

    Args:
        package: Package size (e.g., "0603", "0402")
        resistance_ohms: Resistance value in ohms

    Returns:
        Yageo MPN string
    """
    res_code = format_yageo_mpn_value(resistance_ohms)
    return f"RC{package}FR-07{res_code}"


def generate_resistor_entry(
    ipn_series: str,
    package: str,
    resistance_ohms: float,
    footprint: str,
    voltage: str,
    power: str
) -> dict:
    """
    Generate a single resistor entry.

    Args:
        ipn_series: IPN series number (e.g., "0000" for 0603, "0001" for 0402)
        package: Package size string (e.g., "0603", "0402")
        resistance_ohms: Resistance value in ohms
        footprint: KiCad footprint string
        voltage: Voltage rating
        power: Power rating

    Returns:
        Dictionary with CSV fields
    """
    e96_code = resistance_to_e96_code(resistance_ohms)
    mpn = generate_yageo_mpn(package, resistance_ohms)
    res_display = format_resistance_value(resistance_ohms)
    description = f"{res_display} {package}"

    return {
        'IPN': f"RES-{ipn_series}-{e96_code}",
        'MPN': mpn,
        'Manufacturer': 'Yageo',
        'Description': description,
        'Symbol': 'Device:R_US',
        'Footprint': footprint,
        'Resistance': res_display,
        'Voltage': voltage,
        'Power': power,
        'Tolerance': '1%',
        'Datasheet': 'https://www.yageo.com/upload/media/product/productsearch/datasheet/rchip/PYu-RC_Group_51_RoHS_L_12.pdf'
    }


def generate_e96_series(
    ipn_series: str,
    package: str,
    footprint: str,
    voltage: str,
    power: str
) -> List[dict]:
    """
    Generate complete E96 series for a given package.

    Args:
        ipn_series: IPN series number (e.g., "0000" for 0603)
        package: Package size (e.g., "0603")
        footprint: KiCad footprint string
        voltage: Voltage rating
        power: Power rating

    Returns:
        List of resistor entry dictionaries
    """
    entries = []

    # Generate 0Ω jumper
    entries.append(generate_resistor_entry(
        ipn_series, package, 0, footprint, voltage, power
    ))

    # Generate E96 series across all decades
    for decade_exp in DECADES:
        decade_multiplier = 10 ** decade_exp
        for base_value in E96_VALUES:
            resistance = base_value * decade_multiplier
            # Stop at 10MΩ
            if resistance > 10000000:
                break
            entries.append(generate_resistor_entry(
                ipn_series, package, resistance, footprint, voltage, power
            ))

    return entries


def main():
    """Generate resistor CSV files for 0603 and 0402 packages."""

    # Generate 0603 series (RES-0000)
    print("Generating RES-0000 series (0603 package)...")
    res_0603 = generate_e96_series(
        ipn_series="0000",
        package="0603",
        footprint="Resistor_SMD:R_0603_1608Metric;R_0603_1608Metric_Pad0.98x0.95mm_HandSolder",
        voltage="75V",
        power="100mW"
    )

    # Generate 0402 series (RES-0001)
    print("Generating RES-0001 series (0402 package)...")
    res_0402 = generate_e96_series(
        ipn_series="0001",
        package="0402",
        footprint="Resistor_SMD:R_0402_1005Metric;R_0402_1005Metric_Pad0.72x0.64mm_HandSolder",
        voltage="50V",
        power="63mW"
    )

    # Write 0603 CSV
    output_0603 = "/scratch/bec/parts/database/generated-res-0603.csv"
    print(f"Writing {len(res_0603)} entries to {output_0603}...")
    with open(output_0603, 'w', newline='') as f:
        fieldnames = ['IPN', 'MPN', 'Manufacturer', 'Description', 'Symbol',
                     'Footprint', 'Resistance', 'Voltage', 'Power', 'Tolerance', 'Datasheet']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(res_0603)

    # Write 0402 CSV
    output_0402 = "/scratch/bec/parts/database/generated-res-0402.csv"
    print(f"Writing {len(res_0402)} entries to {output_0402}...")
    with open(output_0402, 'w', newline='') as f:
        fieldnames = ['IPN', 'MPN', 'Manufacturer', 'Description', 'Symbol',
                     'Footprint', 'Resistance', 'Voltage', 'Power', 'Tolerance', 'Datasheet']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(res_0402)

    print("\nGeneration complete!")
    print(f"  0603 (RES-0000): {len(res_0603)} parts")
    print(f"  0402 (RES-0001): {len(res_0402)} parts")
    print(f"  Total: {len(res_0603) + len(res_0402)} parts")


if __name__ == "__main__":
    main()
