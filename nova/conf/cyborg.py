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

from keystoneauth1 import loading as ks_loading
from oslo_config import cfg

from nova.conf import utils as confutils


DEFAULT_SERVICE_TYPE = 'accelerator'
CYBORG_GROUP = 'cyborg'

cyborg_group = cfg.OptGroup(
    CYBORG_GROUP,
    title='Cyborg Options',
    help="""
Configuration options for cyborg (Accelerator as a service).
""")


def register_opts(conf):
    conf.register_group(cyborg_group)
    confutils.register_ksa_opts(conf, cyborg_group, DEFAULT_SERVICE_TYPE)


def list_opts():
    return {
        cyborg_group: (
            ks_loading.get_session_conf_options() +
            ks_loading.get_auth_common_conf_options() +
            ks_loading.get_auth_plugin_conf_options('password') +
            confutils.get_ksa_adapter_opts(DEFAULT_SERVICE_TYPE))
    }
