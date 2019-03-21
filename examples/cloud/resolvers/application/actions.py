import typing

import wtforms

from .resolver import application_resolver


class Action:
    label: str
    form_class: wtforms.Form = None
    formUrl: str = None
    obj: typing.Any = None
    attribute: str = None
    allow_role: str = None
    allowed_states: typing.List[str] = []
    role_message: str = 'You do not have permission to preform this action'
    state_message: str = 'Action not allowed'
    action_message: str = None
    state_attribute: str = 'state'
    state: str = None
    form: wtforms.Form = None

    def __init__(self, source, info, **kwargs):
        """Initialize the form with the source as the object."""
        self.state = getattr(source, self.state_attribute, None)
        self.form = self.form_class(obj=source, **kwargs)

    def is_enabled(self, user) -> bool:
        role_is_set = self.allow_role is not None
        if role_is_set:
            user_has_permission = user.has_role(self.allow_role)
            return self.action_is_allowed and user_has_permission

        return self.action_is_allowed

    @property
    def action_is_allowed(self):
        if not self.allowed_states:
            return True
        return self.state in self.allowed_states

    def tooltip_message(self, user, state=None):
        """Display the tooltip.

        If the action is not allowed return the 'state_message' else
        check if the user has permission and return the 'role_message' if not.
        """
        if not self.action_is_allowed:
            return self.state_message
        elif not self.is_enabled(user):
            return self.role_message
        elif self.action_message:
            return self.action_message
        return None


@application_resolver.resolver('Action')
async def enabled(item, info):
    return item.is_enabled(info.context.user)
