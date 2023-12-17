import wtforms

from ..application import actions


class RenameNetwork(wtforms.Form):
    name = wtforms.TextField(
        "New Name", description="Enter a new name for the network."
    )


class RenameNetworkAction(actions.Action):
    label = "Rename Network"
    form_class = RenameNetwork


NETWORK_ACTIONS = [RenameNetworkAction]
