#!/usr/bin/env python3
#
# Simple script to read output from apcupsd from stdin and print
# JSON blob of useful data.
#

import sys
import re
import os
import time
import argparse
import json


wanted_keys = ('UPSNAME', 'HOSTNAME', 'STATUS', 'BCHARGE', 'TIMELEFT', 'LINEV')

units_re = re.compile(' (Percent|Volts|Minutes|Seconds)$', re.IGNORECASE)

errors = 0
ups_data = {}

for rawline in sys.stdin:
    line = rawline.rstrip()
    try:
        (k, v) = [s.rstrip() for s in line.split(': ', 1)]
        if k in wanted_keys:
            units_match = re.search(units_re, v)
            if units_match:
                units = re.sub(' ', '_', units_match.group(0))
                if units != '':
                    v = re.sub(units_re, '', v)
                    k = k + units.upper()
            ups_data[k] = v
            # print("[" + k + "] -> [" + v + "]")
    except Exception as e:
        # print errors to stderr
        print("Error parsing apcupsd line: {}".format(e), file=sys.stderr)
        print(line, file=sys.stderr)
        errors = errors + 1

if errors > 0:
    ups_data["PARSE_ERRORS"] = errors

ups_data_json = json.dumps(ups_data)
print(ups_data_json)
