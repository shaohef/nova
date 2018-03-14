# Copyright 2013 Intel Corporation
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

""" Example of a PCI alias::

        | [pci]
        | alias = '{
        |   "name": "QuickAssist",
        |   "product_id": "0443",
        |   "vendor_id": "8086",
        |   "device_type": "type-PCI",
        |   "numa_policy": "legacy"
        |   }'

    Aliases with the same name, device_type and numa_policy are ORed::

        | [pci]
        | alias = '{
        |   "name": "QuickAssist",
        |   "product_id": "0442",
        |   "vendor_id": "8086",
        |   "device_type": "type-PCI",
        |   }'

    These two aliases define a device request meaning: vendor_id is "8086" and
    product_id is "0442" or "0443".
    """

import jsonschema
from oslo_serialization import jsonutils
import re
import six

import nova.conf
from nova.api.openstack.placement import lib as placement_lib
from nova import exception
from nova.i18n import _
from nova.network import model as network_model
from nova import objects
from nova.objects import fields as obj_fields
from nova.pci import utils
from nova.objects import fields


XS_RES_PREFIX = 'resources'
XS_TRAIT_PREFIX = 'trait'
XS_KEYPAT = re.compile(r"^(%s)([1-9][0-9]*)?:(.*)$" % '|'.join((XS_RES_PREFIX, XS_TRAIT_PREFIX)))

PCI_NET_TAG = 'physical_network'
PCI_DEVICE_TYPE_TAG = 'dev_type'

DEVICE_TYPE_FOR_VNIC_TYPE = {
    network_model.VNIC_TYPE_DIRECT_PHYSICAL: obj_fields.PciDeviceType.SRIOV_PF
}

CONF = nova.conf.CONF

_ALIAS_CAP_TYPE = ['pci']
_ALIAS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 256,
        },
        # TODO(stephenfin): This isn't used anywhere outside of tests and
        # should probably be removed.
        "capability_type": {
            "type": "string",
            "enum": _ALIAS_CAP_TYPE,
        },
        "product_id": {
            "type": "string",
            "pattern": utils.PCI_VENDOR_PATTERN,
        },
        "vendor_id": {
            "type": "string",
            "pattern": utils.PCI_VENDOR_PATTERN,
        },
        "device_type": {
            "type": "string",
            "enum": list(obj_fields.PciDeviceType.ALL),
        },
        "numa_policy": {
            "type": "string",
            "enum": list(obj_fields.PCINUMAAffinityPolicy.ALL),
        },
    },
    "required": ["name"],
}


def _get_alias_from_config():
    """Parse and validate PCI aliases from the nova config.

    :returns: A dictionary where the keys are device names and the values are
        tuples of form ``(specs, numa_policy)``. ``specs`` is a list of PCI
        device specs, while ``numa_policy`` describes the required NUMA
        affinity of the device(s).
    :raises: exception.PciInvalidAlias if two aliases with the same name have
        different device types or different NUMA policies.
    """
    jaliases = CONF.pci.alias
    aliases = {}  # map alias name to alias spec list
    try:
        for jsonspecs in jaliases:
            spec = jsonutils.loads(jsonspecs)
            jsonschema.validate(spec, _ALIAS_SCHEMA)

            name = spec.pop('name').strip()
            numa_policy = spec.pop('numa_policy', None)
            if not numa_policy:
                numa_policy = obj_fields.PCINUMAAffinityPolicy.LEGACY

            dev_type = spec.pop('device_type', None)
            if dev_type:
                spec['dev_type'] = dev_type

            if name not in aliases:
                aliases[name] = (numa_policy, [spec])
                continue

            if aliases[name][0] != numa_policy:
                reason = _("NUMA policy mismatch for alias '%s'") % name
                raise exception.PciInvalidAlias(reason=reason)

            if aliases[name][1][0]['dev_type'] != spec['dev_type']:
                reason = _("Device type mismatch for alias '%s'") % name
                raise exception.PciInvalidAlias(reason=reason)

            aliases[name][1].append(spec)
    except exception.PciInvalidAlias:
        raise
    except jsonschema.exceptions.ValidationError as exc:
        raise exception.PciInvalidAlias(reason=exc.message)
    except Exception as exc:
        raise exception.PciInvalidAlias(reason=six.text_type(exc))

    return aliases


def _translate_alias_to_requests(alias_spec):
    """Generate complete pci requests from pci aliases in extra_spec."""
    pci_aliases = _get_alias_from_config()

    pci_requests = []
    for name, count in [spec.split(':') for spec in alias_spec.split(',')]:
        name = name.strip()
        if name not in pci_aliases:
            raise exception.PciRequestAliasNotDefined(alias=name)

        count = int(count)
        numa_policy, spec = pci_aliases[name]

        pci_requests.append(objects.InstancePCIRequest(
            count=count,
            spec=spec,
            alias_name=name,
            numa_policy=numa_policy))
    return pci_requests


def get_pci_requests_from_flavor(flavor):
    """Validate and return PCI requests.

    The ``pci_passthrough:alias`` extra spec describes the flavor's PCI
    requests. The extra spec's value is a comma-separated list of format
    ``alias_name_x:count, alias_name_y:count, ... ``, where ``alias_name`` is
    defined in ``pci.alias`` configurations.

    The flavor's requirement is translated into a PCI requests list. Each
    entry in the list is an instance of nova.objects.InstancePCIRequests with
    four keys/attributes.

    - 'spec' states the PCI device properties requirement
    - 'count' states the number of devices
    - 'alias_name' (optional) is the corresponding alias definition name
    - 'numa_policy' (optional) states the required NUMA affinity of the devices

    For example, assume alias configuration is::

        {
            'vendor_id':'8086',
            'device_id':'1502',
            'name':'alias_1'
        }

    While flavor extra specs includes::

        'pci_passthrough:alias': 'alias_1:2'

    The returned ``pci_requests`` are::

        [{
            'count':2,
            'specs': [{'vendor_id':'8086', 'device_id':'1502'}],
            'alias_name': 'alias_1'
        }]

    :param flavor: The flavor to be checked
    :returns: A list of PCI requests
    :rtype: nova.objects.InstancePCIRequests
    :raises: exception.PciRequestAliasNotDefined if an invalid PCI alias is
        provided
    :raises: exception.PciInvalidAlias if the configuration contains invalid
        aliases.
    """
    _rg_by_id = {}

    def get_request_group(ident):
        if ident not in _rg_by_id:
            rq_grp = placement_lib.RequestGroup(use_same_provider=bool(ident))
            _rg_by_id[ident] = rq_grp
        return _rg_by_id[ident]

    def _add_resource(groupid, rclass, amount):
        # Validate the class.
        if not (rclass.startswith(fields.ResourceClass.CUSTOM_NAMESPACE) or
                        rclass in fields.ResourceClass.STANDARD):
            LOG.warning(
                "Received an invalid ResourceClass '%(key)s' in extra_specs.",
                {"key": rclass})
            return
        # val represents the amount.  Convert to int, or warn and skip.
        try:
            amount = int(amount)
            if amount < 0:
                raise ValueError()
        except ValueError:
            LOG.warning(
                "Resource amounts must be nonnegative integers. Received "
                "'%(val)s' for key resources%(groupid)s.",
                {"groupid": groupid, "val": amount})
            return
        get_request_group(groupid).resources[rclass] = amount

    def _add_trait(groupid, trait_name, trait_type):
        # Currently the only valid value for a trait entry is 'required'.
        trait_vals = ('required',)
        # Ensure the value is supported.
        get_request_group(groupid).required_traits.add(trait_name)

    pci_requests = []
    # import pdb; pdb.set_trace()
    if ('extra_specs' in flavor and
            'pci_passthrough:alias' in flavor['extra_specs']):
        pci_requests = _translate_alias_to_requests(
            flavor['extra_specs']['pci_passthrough:alias'])
    elif ('extra_specs' in flavor):
        print("*" * 80)
        print(flavor['extra_specs'])
        payload_example = {
            "instance_uuid": "4047d422-5d2f-432c-b87f-5e1749e95ee6",
            "host": "cyborg-1",
            "resources1:CUSTOM_FPGA_INTEL_VF": "1",
            "resources:CUSTOM_FPGA_INTEL_PF": "1",
            "trait1:CUSTOM_CYBORG_FPGA": "required",
            "trait1:CUSTOM_CYBORG_INTEL": "required",
            "trait1:CUSTOM_CYBORG_CRYPTO": "required"}

        cyborg_resources = {"instance_uuid": None, "host": None}
        for res, val in flavor['extra_specs'].items():
            m = XS_KEYPAT.match(res)
            if not m:
                continue
            k, group, v = m.groups()
            if (not v.startswith("CUSTOM_FPGA_") and not v.startswith("CUSTOM_QAT_")
                and not v.startswith("CUSTOM_CYBORG_")):
                continue
            if k == XS_RES_PREFIX:
                ret._add_resource(group, v, val)

            # Process "trait[$N]"
            elif k == XS_TRAIT_PREFIX:
                _add_trait(group, v, val)
            # cyborg_resources.update({res: val})

        if len(cyborg_resources) > 2:
            from nova.clients.token import token
            from nova.clients.cyborg import cyborg
            tok, data = token.get_token()
            cy = CONF.get("cyborg")
            url = cy.get("url")
            # import pdb; pdb.set_trace()
            r = cyborg.claim_fpgas(tok, cyborg_resources, url=url)
            if r and r.get("deployables", {}).get("pcie_address"):
                for i in r["deployables"]:
                    vendor = r["vendor"][2:]
                    product_id = r["board"][2:]
                    dev_type = 'Type-PF' if r["type"] == "pf" else ""
                    dev_type = 'Type-VF' if r["type"] == "vf" else dev_type
                    request = objects.InstancePCIRequest(
                        count=1,
                        spec=[{'vendor_id': vendor, 'product_id': product_id, 'dev_type': dev_type}],
                        alias_name=r["name"])
                    pci_requests.append(request)

        for k, v in _rg_by_id:
            traits = ",".join(v.required_traits)
            for res, num in v.resources:
                dev_type = 'Type-PF' if res.endswith["_PF"] else ""
                dev_type = 'Type-VF' if res.endswith["_PF"] else dev_type
                request = objects.InstancePCIRequest(
                    count=num,
                    spec=[{'vendor_id': res, 'product_id': traits, 'dev_type': dev_type}],
                    alias_name=r["name"])
                pci_requests.append(request)

        print("=" * 80)
        print(pci_requests)

    return objects.InstancePCIRequests(requests=pci_requests)
