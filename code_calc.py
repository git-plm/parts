#!/usr/bin/python3

import re
import argparse
import os

argparser =  argparse.ArgumentParser(description='Converts Farads (or Ohm) values into variation codes, outputting the code as the last line of output')
argparser.add_argument('value', nargs=1, help="value including 'M', 'k', 'm', '',  'u', 'n' and 'p'")
argparser.add_argument('-r', '--resistor', action='store_true', help="Switches to resistor mode")
argparser.add_argument('-u', '--micro', action='store_true', help="Switches to resistor mode to micro ohms (for shunts)")

unit_decode = {'M': 6, 'k': 3, '': 0, 'm':- 3, 'u': -6, 'n': -9, 'p': -12}
base_unit = -12
base_text = "pF"
extra_unit = "f|F"

args = argparser.parse_args()
value = args.value[0]

if args.resistor or args.micro:
    if args.micro:
        base_unit = -6
        base_text = "uOhm"
    else:
        base_unit = 0
        base_text = "Ohm"
    extra_unit = "Ohm|ohm|R|r"

result = re.search("^\s*([0-9]+)[,.]?([0-9]*)\s*([Mkmunp]?)\s*("+extra_unit+")?\s*$", value)
if (result == None):
    print("Unable to understand {:s} as a value".format(value))
    os._exit(1)

whole   = result.groups()[0]
decimal = result.groups()[1]
unit    = result.groups()[2]
if decimal == None:
    decimal = ""
if unit == None:
    unit = ""
decimal = decimal.rstrip('0') #Ignore decimal trailing 0's, whole trailing is handled by the multiplier

code = whole+decimal

suffix_zeros = unit_decode[unit] - base_unit - len(decimal)
if suffix_zeros < 0:
    print("{:s} has a too small part to encode in a integer base of {:s}".format(value, base_text))
    os._exit(1)
suffix_string = "".ljust(suffix_zeros, "0")

as_base = code+suffix_string
as_base = as_base.lstrip('0') #Ignore prefixed zeros, for instance 0.111uF that would otherwise have to many digits

multiplier = len(as_base)-len(as_base.rstrip('0'))
if multiplier > 9:
    multiplier = 9

code = as_base
if multiplier > 0:
    code = code[0:-multiplier]
code = code.rjust(3, '0')

if len(code) > 3:
    stripped_code = code.rstrip('0')
    if len(stripped_code) > 3:
        print("Too many significant digits in {:s}".format(value))
    else:
        print("{:s} too large to encode in {:s}".format(value, base_text))
    os._exit(1)

print ("Read {:s} as {:s} giving a code of:".format(value, as_base + base_text))
print ("{:s}{:d}".format(code, multiplier))

