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


#
# wrapper for MQTT JSON generation
#
def json_response(data):
    return json.dumps(data)


#
# apcaccess_host() get APC UPS info for given host and port
#
def apcacces_json(host='localhost', port='3551'):

    apcaccess_cmd = '/sbin/apcaccess'
    apcaccess_host = str(host) + ":" + str(port)
    apcaccess_args = [apcaccess_cmd, '-h', apcaccess_host]
    wanted_keys = ('UPSNAME', 'HOSTNAME', 'STATUS', 'BCHARGE',
                   'TIMELEFT', 'LINEV')
    units_re = re.compile(' (Percent|Volts|Minutes|Seconds)$', re.IGNORECASE)
    errors = 0
    ups_data = {}

    # run apcaccess process to get UPS state
    try:
        apcaccess_subprocess = subprocess.Popen(apcaccess_args,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT)
        stdout, stderr = apcaccess_subprocess.communicate()
    except Exception as e:
        ups_data['error_msg'] = "Error parsing apcupsd line: {}".format(e)
        return json_response(ups_data)

    # check the return code
    if (stderr or apcaccess_subprocess.returncode):
        ups_data['errors'] = 1
        ups_data['returncode'] = apcaccess_subprocess.returncode
        if stderr:
            ups_data['error_msg'] = stderr.decode('utf-8')
        elif stdout:
            ups_data['error_msg'] = stdout.decode('utf-8')
        else:
            ups_data['error_msg'] = "Command exited with non-zero return code"
        return json_response(ups_data)

    # parse the response
    for rawline in stdout.decode('utf-8').splitlines():
        line = rawline.rstrip()
        try:
            (k, v) = [s.rstrip() for s in line.split(': ', 1)]
            if k in wanted_keys:
                units_match = re.search(units_re, v)
                units = ''
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
        ups_data["errors"] = errors

    return json_response(ups_data)


for port in [3551, 3552, 3553]:
    print(apcacces_json('localhost', port))
