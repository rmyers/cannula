import logging
import os

import bottle
import cannula
from cannula.datasource.http import FutureSession
from cannula.helpers import get_root_path
from graphql import parse

from session import User
from resolvers.compute import compute_resolver
from resolvers.identity import identity_resolver
from resolvers.navigation import navigation_resolver

PORT = os.getenv('PORT', '8081')
BASE = get_root_path(__name__)
STATIC = os.path.join(BASE, 'static')

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger()

api = cannula.API(__name__, session=FutureSession(), mocks=False)
api.register_resolver(navigation_resolver)
api.register_resolver(compute_resolver)
api.register_resolver(identity_resolver)


@api.context()
class CustomContext(cannula.Context):
    catalog = {
        'compute': {
            'ORD': 'http://openstack:8080/nova/v2.1/1234'
        }
    }
    user = User(catalog, 'fake-token', 'jimmy', '1234')


MAIN_QUERY = parse("""
    query main ($region: String!) {
        servers: computeServers(region: $region) {
            name
            id
            flavor {
                name
                ram
            }
        }
        images: computeImages(region: $region) {
            name
            id
            minRam
        }
        flavors: computeFlavors(region: $region) {
            name
            id
            ram
        }
        nav: getNavigation(active: "dashboard") {
            title
            items {
                active
                icon
                url
                name
                className
                enabled
                disabledMessage
            }
        }
    }
""")


@bottle.route('/')
def main():
    if bottle.request.params.get('xhr'):
        results = api.call_sync(MAIN_QUERY, variables={'region': 'ORD'})
        log.info(results.errors)
        return results.data

    return bottle.template('index')


@bottle.route('/static/<filename:path>')
def send_static(filename):
    return bottle.static_file(filename, root=STATIC)


bottle.run(host='0.0.0.0', port=PORT, debug=True, reloader=True)
