from ..base import OpenStackBase
from .resolver import compute_resolver


@compute_resolver.datasource()
class ComputeFlavors(OpenStackBase):
    catalog_name = "compute"
    resource_name = "ComputeFlavor"

    async def fetchFlavors(self, region=None):
        url = self.get_service_url(region, "flavors/detail")
        resp = await self.get(url)
        return resp.flavors

    async def fetchFlavor(self, region=None, flavor_id=None):
        flavors = await self.fetchFlavors(region)
        data = list(filter(lambda flavor: flavor.id == flavor_id, flavors))
        return data[0]
        # resp = await self.get(f'flavors/{flavor_id}')
        # return resp.flavor


@compute_resolver.resolver("Query")
async def computeFlavors(source, info, region):
    return await info.context.ComputeFlavors.fetchFlavors(region)


@compute_resolver.resolver("Query")
async def computeFlavor(source, info, id, region):
    return await info.context.ComputeFlavors.fetchFlavor(region, flavor_id=id)


@compute_resolver.resolver("ComputeServer")
async def flavor(server, info):
    return await info.context.ComputeFlavors.fetchFlavor(
        server.region, server.flavor.id
    )
