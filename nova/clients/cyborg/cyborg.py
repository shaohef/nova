#!/usr/bin/python

import requests
import json
import os
import random
import uuid as uuidlib
import sys


HOST = "127.0.0.1"
HOSTURL = "http://%s" % HOST
BASEURL = "http://%s/v1" % HOST
# cyborg = CONF.get("cyborg")
# cyborg.get("url")


def pretty_print(r):
    if not r.ok:
        print r.content
        return
    data = r.json()
    res = json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
    print res
    return data


def claim_fpgas(token, payload={}, url=BASEURL):
    """
    payload = {
        "instance_uuid": "4047d422-5d2f-432c-b87f-5e1749e95ee6",
        "host": "cyborg-1",
        "resources1:CUSTOM_FPGA_INTEL_VF": "1",
        "resources:CUSTOM_FPGA_INTEL_PF": "1",
        "trait1:CUSTOM_CYBORG_FPGA": "required",
        "trait1:CUSTOM_CYBORG_INTEL": "required",
        "trait1:CUSTOM_CYBORG_CRYPTO": "required"
    }
    """
    payload = {
        "instance_uuid": "4047d422-5d2f-432c-b87f-5e1749e95ee6",
        "host": "cyborg-1",
        "resources1:CUSTOM_FPGA_INTEL_VF": "1",
        "resources:CUSTOM_FPGA_INTEL_PF": "1",
        "trait1:CUSTOM_CYBORG_FPGA": "required",
        "trait1:CUSTOM_CYBORG_INTEL": "required",
        "trait1:CUSTOM_CYBORG_CRYPTO": "required"
    } if not payload else payload
    HEADERS = {"Content-Type": "application/json",
               "Accept": "application/json",
               "X-Auth-Token": token}
    url = os.path.join(url, "deployables/allocations")
    r = requests.post(url, data=json.dumps(payload), headers=HEADERS)
    if r.ok:
       return r.json()
    res = pretty_print(r)
