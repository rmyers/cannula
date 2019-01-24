
from ..base import OpenStackBase
from .resolver import compute_resolver


@compute_resolver.datasource()
class ComputeImages(OpenStackBase):

    catalog_name = 'compute'
    resource_name = 'ComputeImage'

    async def fetchImages(self, region=None):
        url = self.get_service_url(region, 'images/detail')
        resp = await self.get(url)
        return resp.images

    async def fetchImage(self, region=None, image_id=None):
        images = await self.fetchImages(region)
        data = list(filter(lambda image: image.id == image_id, images))
        return data[0]
        # resp = await self.get(f'images/{image_id}')
        # return resp.image


@compute_resolver.resolver('Query')
async def computeImages(source, info, region):
    return await info.context.ComputeImages.fetchImages(region)


@compute_resolver.resolver('Query')
async def computeImage(source, info, id, region):
    return await info.context.ComputeImages.fetchImage(region, image_id=id)


@compute_resolver.resolver('ComputeServer')
async def image(server, info):
    return await info.context.ComputeImages.fetchImage(
        server.region,
        server.image.id
    )
