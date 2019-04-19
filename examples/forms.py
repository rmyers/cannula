import decimal
import pprint
import time

from graphql import GraphQLError
from wtforms import Form, StringField, DecimalField, validators

import cannula
from cannula.datasource import forms


WIDGETS = {
    '12345': {
        'name': 'widgety',
        'price': decimal.Decimal('4.90'),
    }
}


# First create a resolver that uses the WTFormsResolver class
my_resolver = cannula.datasource.forms.WTFormsResolver(__name__, schema='''
    type Widget {
        name: String
        price: Float
    }
    type Query {
        _empty: String
    }
    type Mutation {
        _empty: String
    }
''')


# Next use the register_form decorator on a wtform class. The args are used
# to generate a set of key/value pairs that are passed to the resolver function.
# This is so that you can fetch the object that the form is for.
@my_resolver.register_form(args=['id'])
class UpdateWidget(Form):
    name = StringField('Widget Name', validators=[validators.Length(max=25)])
    price = DecimalField('Widget Price', validators=[validators.NumberRange(min=5.3)])

    class Meta:
        name = "Barney"
        action = "lol"


@my_resolver.resolver('Query')
async def getUpdateWidgetForm(source, info, args):
    # Turn the args list back into a dict
    kwargs = forms.unwrap_args(args)

    # Use the kwargs to fetch the resource like:
    # widget = await info.context.WidgetDatasource.fetch(kwargs['id'])

    # Get our object from the local datastore
    widget = WIDGETS.get(kwargs['id'])

    # Use your custom wtform like normal, we have a dict rather than an object.
    # We could pass `obj=widget` if it wasn't fake.
    update_form = info.context.UpdateWidget.form(**widget)
    return update_form


@my_resolver.resolver('Mutation')
async def postUpdateWidgetForm(source, info, args, form=None):
    kwargs = forms.unwrap_args(args)

    update_form = info.context.UpdateWidget.form(form)
    if not update_form.validate():
        # ERROR!!
        raise GraphQLError("Update Widget Error", extensions=update_form.errors)

    # Actually update the object in the datastore
    WIDGETS[kwargs['id']] = {
        'name': update_form.name.data,
        'price': update_form.price.data,
    }
    return update_form


api = cannula.API(__name__, resolvers=[
    my_resolver
])


results = api.call_sync(
    my_resolver.get_form_query('UpdateWidget', id='12345'),
    request=None,
)

print('WIDGETS BEFORE UPDATE')
print(WIDGETS)

print('DATA:')
pprint.pprint(results.data, compact=True, width=200)
print('ERRORS:')
pprint.pprint(results.errors)


class DummyPostData(dict):
    """Mimic Post Data aka request.POST or request.form()"""

    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v


# Post an update with invalid inputs
fake_post_data = DummyPostData(name='darny', price=5.0)
results = api.call_sync(
    my_resolver.get_form_mutation('UpdateWidget', id='12345'),
    variables={'form': forms.FormDataWrapper(fake_post_data)},
    request=None,
)
print(results)

# Post an update with valid inputs
fake_post_data = DummyPostData(name='darny', price=decimal.Decimal('6.89'))
results = api.call_sync(
    my_resolver.get_form_mutation('UpdateWidget', id='12345'),
    variables={'form': forms.FormDataWrapper(fake_post_data)},
    request=None,
)
print(results)


print('WIDGETS AFTER UPDATE')
print(WIDGETS)
