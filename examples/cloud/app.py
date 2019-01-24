import collections
import logging
import os

import bottle
import cannula
from graphql import parse

import session
from resolvers.compute import compute_resolver
from resolvers.dashboard import dashboard_resolver
from resolvers.identity import identity_resolver
from resolvers.navigation import navigation_resolver
from resolvers.network import network_resolver

PORT = os.getenv('PORT', '8081')
STATIC = os.path.join(os.getcwd(), 'static')
USE_MOCKS = bool(os.getenv('USE_MOCKS', False))

logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger('application')

api = cannula.API(__name__, context=session.OpenStackContext, mocks=USE_MOCKS)

# Order matters for these applications you extend
api.register_resolver(navigation_resolver)
api.register_resolver(compute_resolver)
api.register_resolver(identity_resolver)
api.register_resolver(network_resolver)
api.register_resolver(dashboard_resolver)


def format_errors(errors):
    """Return a dict object of the errors.

    If there is a path(s) in the error then return a dict with the path
    as a key so that it is easier on the client side code to display the
    error with the correct data.
    """
    if errors is None:
        return {}

    formatted_errors = collections.defaultdict(list)

    for err in errors:
        if err.path is not None:
            for path in err.path:
                formatted_errors[path].append(err.formatted)
        else:
            # All other errors are probably graphql errors such as
            # an unknown query or unknown field on a type.
            formatted_errors['errors'].append(err.formatted)

    return formatted_errors


DASHBOARD_QUERY = parse("""
    fragment quotaFields on QuotaChartData {
        datasets {
            data
            backgroundColor
        }
        labels
    }
    query main ($region: String!) {
        serverQuota: quotaChartData(resource: "ComputeServers") {
            ...quotaFields
        }
        networkQuota: quotaChartData(resource: "Networks") {
            ...quotaFields
        }
        resources: resources(region: $region) {
            __typename
            ... on ComputeServer {
                name
                id
            }
            ... on Network {
                name
                id
            }
        }
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
    if bottle.request.params.get('xhr'):
        results = api.call_sync(
            DASHBOARD_QUERY,
            variables={'region': 'us-east'},
            request=bottle.request
        )

        resp = {
            'errors': format_errors(results.errors),
            'data': results.data or {}
        }

        return resp

    if not session.is_authenticated(bottle.request):
        return bottle.redirect('/')

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
