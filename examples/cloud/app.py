import logging
import os

import cannula
import uvicorn
from cannula.middleware import MockMiddleware, DebugMiddleware
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import session
from api import api

PORT = os.getenv('PORT', '8081')
STATIC = os.path.join(os.getcwd(), 'static')
USE_MOCKS = bool(os.getenv('USE_MOCKS', False))
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))

logging.basicConfig(level=logging.DEBUG)
templates = Jinja2Templates(directory='templates')

LOG = logging.getLogger('application')

app = Starlette(debug=True)
app.mount('/static', StaticFiles(directory='static'), name='static')


@app.route('/dashboard')
async def dashboard(request):
    LOG.info(request.headers)
    if 'xhr' in request.query_params:
        results = await api.call(
            api.load_query('dashboard'),
            variables={'region': 'us-east'},
            request=request
        )

        resp = {
            'errors': cannula.format_errors(results.errors),
            'data': results.data or {}
        }

        return JSONResponse(resp)

    if not session.is_authenticated(request):
        return RedirectResponse('/')

    return templates.TemplateResponse('index.html', {'request': request})


@app.route('/simple')
async def simple(request):
    if 'xhr' in request.query_params:
        results = await api.call(
            api.load_query('simple'),
            variables={'region': 'us-east'},
            request=request
        )

        resp = {
            'errors': cannula.format_errors(results.errors),
            'data': results.data or {}
        }

        return JSONResponse(resp)

    if not session.is_authenticated(request):
        return RedirectResponse('/')

    return templates.TemplateResponse('simple.html', {'request': request})


@app.route('/')
async def login(request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.route('/', methods=['POST'])
async def do_login(request):
    form = await request.form()
    username = form.get('username')
    password = form.get('password')
    LOG.info(f'Attempting login for {username}')
    response = await session.login(request, username, password, api)
    return response


@app.route('/network/action/{form_name}')
async def network_action_form_get(request):
    form_name = request.path_params['form_name']
    query = api.get_form_query(form_name, **request.query_params)
    results = await api.call(
        query,
        request=request
    )

    resp = {
        'errors': cannula.format_errors(results.errors),
        'data': results.data or {}
    }

    return JSONResponse(resp)


if __name__ == '__main__':
    if USE_MOCKS:
        api.middleware.insert(0, MockMiddleware(mock_all=False))
    uvicorn.run(app, host='0.0.0.0', port=int(PORT), debug=True, log_level=logging.INFO)
