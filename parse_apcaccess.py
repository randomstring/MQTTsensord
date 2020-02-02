#!/usr/bin/env python3
#
# Simple script to read output from apcaccess from stdin and print
# JSON blob of useful data.
#

import sys
import re
import subprocess
import json
import os
import time
import argparse


apcaccess_cmd = '/sbin/apcaccess'
apcaccess_args = [apcaccess_cmd, '-h', 'localhost:3551']

wanted_keys = ('UPSNAME', 'HOSTNAME', 'STATUS', 'BCHARGE', 'TIMELEFT', 'LINEV')

units_re = re.compile(' (Percent|Volts|Minutes|Seconds)$', re.IGNORECASE)

errors = 0
ups_data = {}

# TODO: add try/except wrapper
apcaccess_subprocess = subprocess.Popen(apcaccess_args,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
stdout, stderr = apcaccess_subprocess.communicate()
# print(stdout.decode('utf-8'))

if stderr:
    ups_data['errors_cmd'] = 1
    ups_data['error_msg'] = "apcaccess writing to stderr"
    print(stderr.decode('utf-8'))

# for rawline in sys.stdin:
for rawline in stdout.decode('utf-8').splitlines():
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
