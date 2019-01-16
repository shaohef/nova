# Copyright 2019 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from oslo_log import log as logging

from nova import utils

"""
   Note on object relationships:
   1 device profile (DP) has D >= 1 request groups (just as a flavor
       has many request groups).
   Each DP request group corresponds to exactly 1 numbered request
       group (RG) in the request spec.
   Each numbered RG corresponds to exactly one resource provider (RP).
   A DP request group may request A >= 1 accelerators, and so result
       in the creation of A ARQs.
   Each ARQ corresponds to exactly 1 DP request group.

   A device profile is a dictionary:
   { "name": "mydpname",
     "uuid": <uuid>,
     "groups": [ <device_profile_request_group> ]
   }

   A device profile group is a dictionary too:
    { "resources:CUSTOM_ACCELERATOR_FPGA": "2",
      "resources:CUSTOM_LOCAL_MEMORY": "1",
      "trait:CUSTOM_INTEL_PAC_ARRIA10": "required",
      "trait:CUSTOM_FUNCTION_NAME_FALCON_GZIP_1_1": "required",
       # 0 or more Cyborg properties
      "accel:bitstream_id": "FB021995_BF21_4463_936A_02D49D4DB5E5"
   }

   See cyborg/cyborg/objects/device_profile.py for more details.
"""

LOG = logging.getLogger(__name__)


def get_client():
    return _CyborgClient()


def get_device_profile_group_requester_id(dp_group_id):
    """Return the value to use in objects.RequestGroup.requester_id.

       The requester_id is used to match device profile groups from
       Cyborg to the request groups in request spec.
    """
    req_id = "device_profile_" + str(dp_group_id)
    return req_id


class _CyborgClient(object):

    DEVICE_PROFILE_URL = "/device_profiles"
    ARQ_URL = "/accelerator_requests"

    def __init__(self):
        self._client = utils.get_ksa_adapter('accelerator')

    def get_device_profile_groups(self, dp_name):
        """Get list of profile group objects from the device profile.

           Cyborg API returns: {"device_profiles": [<device_profile>]}
           See module notes above for further details.

           :param dp_name: string: device profile name
           :returns [<device_profile_group>]
        """
        if dp_name is None or dp_name == '':
            raise RuntimeError('Device profile name is invalid %s' % dp_name)

        url = self.DEVICE_PROFILE_URL
        query = {"name": dp_name}
        r = self._client.get(url, params=query)

        if not r:
            raise RuntimeError('Failed to get device profile from Cyborg')

        dp_list = r.json().get('device_profiles')
        if dp_list is None:
            LOG.error('Expected 1 device profile but got nothing')
            return []
        if len(dp_list) != 1:
            LOG.error('Expected 1 device profile but got %d', len(dp_list))
            return []

        return dp_list[0]['groups']
