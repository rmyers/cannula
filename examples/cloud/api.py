"""
Example Cannula API Usage
=========================

This is module that joins our schema and our resolvers. I have this in a
different module so that we can import it separately for testing.
"""

import cannula

from resolvers.application import application_resolver
from resolvers.compute import compute_resolver
from resolvers.dashboard import dashboard_resolver
from resolvers.identity import identity_resolver
from resolvers.network import network_resolver
from resolvers.volume import volume_resolver
from session import OpenStackContext


api = cannula.API(
    __name__,
    resolvers=[
        application_resolver,
        compute_resolver,
        identity_resolver,
        network_resolver,
        volume_resolver,
        dashboard_resolver,
    ],
    context=OpenStackContext,
)
