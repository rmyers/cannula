import json
import logging
import os
import time

import bottle
import cannula
import requests
from cannula.datasource.rest import HTTPDataSource, FutureSession
from cannula.helpers import get_root_path
from requests_futures.sessions import FuturesSession

from session import User
from resolvers.compute import compute_resolver

PORT = os.getenv('PORT', '8081')
BASE = get_root_path(__name__)
STATIC = os.path.join(BASE, 'static')

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger()

api = cannula.API(__name__, session=FutureSession())
api.register_resolver(compute_resolver)


@api.context()
class CustomContext(cannula.Context):
    catalog = {
        'compute': {
            'ORD': 'http://openstack:8080/nova/v2.1/1234'
        }
    }
    user = User(catalog, 'fake-token', 'jimmy', '1234')


@bottle.route('/')
def main():
    optional_query = """{
        servers: computeServers(region: "ORD") {
            name
            flavor {
                name
                ram
            }
        }
        flavors: computeFlavors(region: "ORD") {
            name
            ram
        }
        images: computeImages(region: "ORD") {
            name
            minRam
        }
    }
    """
    if bottle.request.params.get('xhr'):
        log.info('here?')
        results = api.call_sync(optional_query)
        return results.data

    return bottle.template('index')


@bottle.route('/static/<filename:path>')
def send_static(filename):
    return bottle.static_file(filename, root=STATIC)


bottle.run(host='0.0.0.0', port=PORT, debug=True, reloader=True)
