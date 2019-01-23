import logging

from .resolver import compute_resolver
from ..base import OpenStackBase

LOG = logging.getLogger(__name__)


@compute_resolver.datasource()
class ComputeServers(OpenStackBase):

    catalog_name = 'compute'

    async def fetchServers(self, region=None):
        url = self.get_service_url(region, 'servers/detail')
        resp = await self.get(url)
        for server in resp.servers:
            server.region = region
        return resp.servers

    async def fetchLimits(self):
        LOG.info('Fetching Limits')
        east_url = self.get_service_url('us-east', 'limits')
        resp = await self.get(east_url)
        return resp.servers


@compute_resolver.resolver('Query')
async def computeServers(source, info, region):
    LOG.info('in computeServers')
    return await info.context.ComputeServers.fetchServers(region)
