import logging

from .resolver import compute_resolver
from ..base import OpenStackBase

LOG = logging.getLogger(__name__)


@compute_resolver.datasource()
class ComputeServers(OpenStackBase):

    catalog_name = 'compute'
    resource_name = 'ComputeServer'

    async def fetchServers(self, region=None):
        url = self.get_service_url(region, 'servers/detail')
        resp = await self.get(url)
        servers = resp.servers
        for server in servers:
            server.region = region
        return servers

    async def fetchLimits(self):
        east_url = self.get_service_url('us-east', 'limits')
        resp = await self.get(east_url)
        return resp.servers


@compute_resolver.resolver('Query')
async def computeServers(source, info, region):
    return await info.context.ComputeServers.fetchServers(region)
