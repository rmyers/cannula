import json
import logging

import cannula

from ..base import OpenStackBase

LOG = logging.getLogger(__name__)

identity_resolver = cannula.Resolver(__name__)


@identity_resolver.datasource()
class Identity(OpenStackBase):
    # Identity is special because we have to login first
    # to get the service catalog for the other services. That is why
    # we must specify the base url here.
    base_url = "http://openstack:8080/v3"

    async def login(self, username, password):
        body = {
            "auth": {
                "identity": {
                    "password": {"user": {"name": username, "password": password}}
                }
            }
        }
        resp = await self.post("auth/tokens", body=body)
        resp.token.authToken = resp.headers.get("X-Subject-Token")
        return resp.token

    async def did_receive_response(self, response, request):
        response_object = await super().did_receive_response(response, request)
        # Add the headers to the response object
        response_object.headers = response.headers
        return response_object


@identity_resolver.resolver("Mutation")
async def login(source, info, username, password):
    LOG.info("in login mutation")
    return await info.context.Identity.login(username, password)
