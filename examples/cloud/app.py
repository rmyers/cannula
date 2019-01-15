import logging
import os

import bottle
import cannula
from graphql import parse

import session
from resolvers.compute import compute_resolver
from resolvers.identity import identity_resolver
from resolvers.navigation import navigation_resolver

PORT = os.getenv('PORT', '8081')
STATIC = os.path.join(os.getcwd(), 'static')
USE_MOCKS = bool(os.getenv('USE_MOCKS', False))

logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger('application')

api = cannula.API(__name__, context=session.CustomContext, mocks=USE_MOCKS)
api.register_resolver(navigation_resolver)
api.register_resolver(compute_resolver)
api.register_resolver(identity_resolver)


DASHBOARD_QUERY = parse("""
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


@bottle.route('/dashboard')
def dashboard():
    if not session.is_authenticated(bottle.request):
        return bottle.redirect('/')

    if bottle.request.params.get('xhr'):
        results = api.call_sync(
            DASHBOARD_QUERY,
            variables={'region': 'us-east'},
            request=bottle.request
        )
        if results.errors:
            LOG.error(results.errors)
        return results.data

    return bottle.template('index')


@bottle.route('/')
def login():
    return bottle.template('login')


@bottle.post('/')
def do_login():
    username = bottle.request.forms.get('username')
    password = bottle.request.forms.get('password')
    LOG.info(f'Attempting login for {username}')
    session.login(username, password, api)
    bottle.redirect("/dashboard")


@bottle.route('/static/<filename:path>')
def send_static(filename):
    return bottle.static_file(filename, root=STATIC)


bottle.run(host='0.0.0.0', port=PORT, debug=True, reloader=True)
