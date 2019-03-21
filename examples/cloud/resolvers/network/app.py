from cannula.dataloaders import forms
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .forms import RenameNetwork

network_app = Starlette(debug=True)

RENAME_QUERY = forms.parse_form_query("""
    query getForm($networkId: String!) {
        getRenameNetworkForm(id: $networkId) {
            ...formQueryFragment
        }
    }
""")

@network_app.add_route('/{id}/rename', name='rename_network', methods=['GET', 'POST'])
async def rename_network(parameter_list):

