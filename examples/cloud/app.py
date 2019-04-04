import collections
import logging
import os
import sys

import bottle
import cannula
from cannula.datasource import forms
from graphql import parse

from starlette import status
from starlette.applications import Starlette
from starlette.background import BackgroundTasks
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.types import ASGIInstance, Receive, Scope, Send

import session
from resolvers.application import application_resolver
from resolvers.compute import compute_resolver
from resolvers.dashboard import dashboard_resolver
from resolvers.identity import identity_resolver
from resolvers.network import network_resolver
from resolvers.volume import volume_resolver

PORT = os.getenv('PORT', '8081')
STATIC = os.path.join(os.getcwd(), 'static')
USE_MOCKS = bool(os.getenv('USE_MOCKS', False))

logging.basicConfig(level=logging.DEBUG)
templates = Jinja2Templates(directory='templates')

LOG = logging.getLogger('application')

mock_objects = {
    'ComputeServer': {
        '__typename': 'ComputeServer',
        'name': 'frank',
        'id': '1233455',
    }
}

api = cannula.API(__name__, context=session.OpenStackContext, mocks=USE_MOCKS, mock_objects=mock_objects)

# Order matters for these applications you extend
api.register_resolver(application_resolver)
api.register_resolver(compute_resolver)
api.register_resolver(identity_resolver)
api.register_resolver(network_resolver)
api.register_resolver(volume_resolver)
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
        error_formatted = err.formatted
        error_message = error_formatted['message']
        if err.path is not None:
            for path in err.path:
                if error_message not in formatted_errors[path]:
                    formatted_errors[path].append(error_message)

        if error_message not in formatted_errors['errors']:
            formatted_errors['errors'].append(error_message)

    return formatted_errors


DASHBOARD_QUERY = parse("""
    # This is a fragment for our quota charts so we don't have to repeat it.
    fragment quotaFields on QuotaChartData {
        datasets {
            data
            backgroundColor
        }
        labels
    }
    # Status fragment for our resources
    fragment statusFields on ApplicationStatus {
        label
        color
        working
        icon
        tooltip
    }
    fragment actionFields on Action {
        label
        formUrl
        icon
        enabled
        tooltip
    }
    query main ($region: String!) {
        serverQuota: quotaChartData(resource: "ComputeServers") {
            ...quotaFields
        }
        networkQuota: quotaChartData(resource: "Networks") {
            ...quotaFields
        }
        volumeQuota: quotaChartData(resource: "Volumes") {
            ...quotaFields
        }
        resources: resources(region: $region) {
            __typename
            ... on ComputeServer {
                name
                id
                appStatus {
                    ...statusFields
                }
            }
            ... on Network {
                name
                id
                appStatus {
                    ...statusFields
                }
                appActions {
                    ...actionFields
                }
            }
            ... on Volume {
                name
                id
                appStatus {
                    ...statusFields
                }
                appActions {
                    ...actionFields
                }
            }
        }
        images: computeImages(region: $region) {
            name
            minRam
        }
        flavors: computeFlavors(region: $region) {
            name
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


app = Starlette(debug=True)
app.mount('/static', StaticFiles(directory='static'), name='static')


@app.route('/dashboard')
async def dashboard(request):
    if 'xhr' in request.query_params:
        results = await api.call(
            DASHBOARD_QUERY,
            variables={'region': 'us-east'},
            request=request
        )

        resp = {
            'errors': format_errors(results.errors),
            'data': results.data or {}
        }

        return JSONResponse(resp)

    if not session.is_authenticated(request):
        return RedirectResponse('/')

    return templates.TemplateResponse('index.html', {'request': request})


@app.route('/')
async def login(request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.route('/', methods=['POST'])
async def do_login(request):
    form = await request.form()
    LOG.info(f'{form}: {dir(form)}')
    username = form.get('username')
    password = form.get('password')
    LOG.info(f'Attempting login for {username}')
    response = await session.login(request, username, password, api)
    return response


@app.route('/network/action/{form_name}')
async def network_action_form_get(request):
    form_name = request.path_params['form_name']
    query = network_resolver.get_form_query(form_name, **request.query_params)
    results = await api.call(
        query,
        request=request
    )

    resp = {
        'errors': format_errors(results.errors),
        'data': results.data or {}
    }

    return JSONResponse(resp)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8081, debug=True, log_level=logging.INFO)
