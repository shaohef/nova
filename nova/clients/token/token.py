#!/usr/bin/python
import requests
import json
import os

from nova.conf import CONF


SC = CONF.get("keystone_authtoken")
SC.get("username")

# import pdb; pdb.set_trace()
CAFILE = SC.get("cafile") if SC else None
OS_USERNAME = SC.get("username") if SC else None
OS_PASSWORD = SC.get("password") if SC else None
OS_PROJECT_NAME = SC.get("project_name") if SC else None
OS_AUTH_URL = SC.get("auth_url") if SC else None
OS_AUTH_TYPE = SC.get("auth_type") if SC else "password"

OS_PROJECT_DOMAIN_ID = SC.get("project_domain_name") if SC else "Default"
OS_USER_DOMAIN_ID = SC.get("user_domain_name") if SC else "Default"
# OS_REGION_NAME =  SC.get("region_name") if SC else "RegionOne"

# NOTE hardcode.
TOKEN_URL = os.path.join(OS_AUTH_URL, "v3/auth/tokens")
SERVICES_URL = os.path.join(OS_AUTH_URL, "v3/services")
ENDPOINTS_URL = os.path.join(OS_AUTH_URL, "v3/endpoints")

AUTH_BODY = {
    "auth": {
        "identity": {
            "methods": [
                OS_AUTH_TYPE
            ],
            "password": {
                "user": {
                    "name": OS_USERNAME,
                    "domain": {
                        "name": OS_USER_DOMAIN_ID
                    },
                    "password": OS_PASSWORD
                }
            }
        },
        "scope": {
            "project": {
                "name": OS_PROJECT_NAME,
               "domain": {
                   "name": OS_PROJECT_DOMAIN_ID
               }
            }
        }
    }
}


def get_token():
    """ Return token and data.

        project_id = data["token"]["project"]["id"]
        user_id = data["token"]["user"]["id"]
    """
    headers = {"Content-Type": "application/json"}
    # import pdb; pdb.set_trace()
    r = requests.post(TOKEN_URL, data=json.dumps(AUTH_BODY), headers=headers)
    if r.ok:
        data = r.json()
        # print json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
        return r.headers['X-Subject-Token'], data
    return None, {}


def get_service_url(token, service):
    headers = {"Content-Type": "application/json",
               "X-Auth-Token": token}
    r = requests.get(SERVICES_URL, headers=headers, params={"type": service})
    if not r.ok:
        return None
    data = r.json()
    services_id = None
    if data["services"]:
        services_id = data["services"][0]["id"]

    if not services_id:
        return
    r = requests.get(ENDPOINTS_URL, headers=headers, params={"service_id": services_id})
    if not r.ok:
        return None
    data = r.json()
    if data["endpoints"]:
        return data["endpoints"][0]["url"]


def get_image_url(token):
    return get_service_url(token, "image")


def get_placement_url(token):
    return get_service_url(token, "placement")
