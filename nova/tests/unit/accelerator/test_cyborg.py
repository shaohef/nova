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
from nova.accelerator import cyborg
from nova import test


class CyborgTestCase(test.NoDBTestCase):

    def test_get_client(self):
        # Set up some ksa conf options
        region = 'MyRegion'
        endpoint = 'http://endpoint.com:1234'
        self.flags(group='cyborg',
                   region_name=region,
                   endpoint_override=endpoint)
        # Ensure we don't get a stale client from some other init
        cyborg._CYBORG_CLIENT = None
        client = cyborg.get_client()
        # Dig into the ksa adapter a bit to ensure the conf options got through
        # We don't bother with a thorough test of get_ksa_adapter - that's done
        # elsewhere - this is just sanity-checking that we spelled things right
        # in the conf setup.
        self.assertEqual('accelerator', client._client.service_type)
        self.assertEqual(region, client._client.region_name)
        self.assertEqual(endpoint, client._client.endpoint_override)
        # Verify singleton behavior
        self.assertIs(client, cyborg.get_client())
