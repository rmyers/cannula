import asyncio
import itertools
import logging
import typing

import cannula
import wtforms
from cannula.datasource.forms import WTFormsResolver

from ..application import status, actions
from ..base import OpenStackBase

LOG = logging.getLogger(__name__)

network_resolver = WTFormsResolver(__name__)


@network_resolver.datasource()
class Network(OpenStackBase):

    catalog_name = 'network'

    async def fetchNetworks(self, region=None):
        url = self.get_service_url(region, 'v2.0/networks.json')
        resp = await self.get(url)
        networks = resp.networks
        for network in networks:
            network.region = region
        return networks

    async def fetchLimits(self):
        east_url = self.get_service_url('us-east', 'v2.0/limits.json')
        resp = await self.get(east_url)
        return resp.networks


@network_resolver.datasource()
class Subnet(OpenStackBase):

    catalog_name = 'network'

    async def fetchSubnet(self, region, subnet_id):
        url = self.get_service_url(region, 'v2.0/subnets.json')
        resp = await self.get(url)
        subnets = resp.subnets
        for subnet in subnets:
            if subnet.id == subnet_id:
                return subnet


@network_resolver.resolver('Query')
async def getNetworks(source, info, region):
    return await info.context.Network.fetchNetworks(region)


@network_resolver.resolver('Network')
async def subnets(network, info):
    awaitables = []
    for _id in network.subnets:
        awaitables.append(info.context.Subnet.fetchSubnet(network.region, _id))

    results = await asyncio.gather(awaitables)
    return itertools.chain(*results)


@network_resolver.resolver('Network')
async def appStatus(network, info):
    return status.Status(
        label=network.status,
    )


class RenameNetwork(wtforms.Form):
    name = wtforms.TextField(
        'New Name',
        description="Enter a new name for the network."
    )


class RenameNetworkAction(actions.Action):
    label = "Rename Network"
    form_class = RenameNetwork


NETWORK_ACTIONS = [
    RenameNetworkAction
]


@network_resolver.resolver('Network')
async def appActions(network, info):
    return [action(network, info) for action in NETWORK_ACTIONS]
