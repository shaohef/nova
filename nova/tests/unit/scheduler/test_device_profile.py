# Copyright (c) 2014 Red Hat, Inc.
# All Rights Reserved.
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

from nova.scheduler import utils
from nova import test
from nova.tests.unit import fake_request_spec

"""Tests for Device Profiles."""


class DeviceProfileTestCase(test.NoDBTestCase):

    def _test_no_device_profile(self):
        """If the flavor has no device profile, the call to
           add request groups must be a no-op.
        """
        spec_obj = fake_request_spec.fake_spec_obj()
        rr = utils.ResourceRequest()
        prev_rr = rr
        rr.add_request_groups_from_device_profile(spec_obj)
        self.assertIs(prev_rr, rr)  # Compare by identity
