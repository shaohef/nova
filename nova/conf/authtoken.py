# Copyright 2017 Intel.
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

from oslo_config import cfg

from nova.i18n import _

opts = [
    cfg.StrOpt('auth_url',
               # default=6666,
               help=_("the url of auth.")),
    cfg.StrOpt('auth_type',
               # default=6666,
               help=_("auth_type, it can be password.")),
    cfg.StrOpt('username',
               help=_("The cyborg username as service project")),
    cfg.StrOpt('password',
               help=_("The password of cyborg username.")),
    cfg.StrOpt('project_name',
               help=_("project name")),
    cfg.StrOpt('user_domain_name',
               help=_("user domain name")),
    cfg.StrOpt('project_domain_name',
               help=_("project domain id")),
    cfg.StrOpt('cafile',
               help=_("ca file")),
]

opt_group = cfg.OptGroup(name='keystone_authtoken',
                         title='Options for the nova keystone_authtoken.')


def register_opts(conf):
    conf.register_group(opt_group)
    conf.register_opts(opts, group=opt_group)
