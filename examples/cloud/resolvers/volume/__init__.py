import logging

import cannula

from ..application import status
from ..base import OpenStackBase

LOG = logging.getLogger(__name__)

volume_resolver = cannula.Resolver(__name__)


@volume_resolver.datasource()
class Volume(OpenStackBase):
    catalog_name = "volume"

    async def fetchVolumes(self, region=None):
        url = self.get_service_url(region, "volumes/detail")
        resp = await self.get(url)
        volumes = resp.volumes
        for volume in volumes:
            volume.region = region
        return volumes

    async def fetchLimits(self):
        east_url = self.get_service_url("us-east", "limits")
        resp = await self.get(east_url)
        return resp.limits


@volume_resolver.resolver("Query")
async def getVolumes(source, info, region):
    return await info.context.Volume.fetchVolumes(region)


@volume_resolver.resolver("Volume")
async def appStatus(volume, info):
    return status.Status(
        label=volume.status,
    )
