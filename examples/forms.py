import pprint
import urllib.parse

from graphql import parse, GraphQLError
from wtforms import (
    Form,
    BooleanField,
    StringField,
    DecimalField,
    validators,
    SelectMultipleField,
    FormField,
    FieldList,
)

import cannula
from cannula.datasource import forms

my_resolver = cannula.datasource.forms.WTFormsResolver(__name__, schema='''
    type Widget {
        name: String
    }
    extend type Mutation {
        updateWidget(form: String): Widget
    }
''')

my_other_resolver = cannula.datasource.forms.WTFormsResolver(__name__, schema='''
    type WidgetRedux {
        name: String
    }
''')

def is_42(form, field):
    if field.data != 42:
        raise validators.ValidationError('Must be 42')


class Other(Form):
    name = StringField('Widget Namer', validators=[validators.Length(max=25), is_42])

    class Meta:
        name = 'Frank'


@my_resolver.register_form(args=['id'])
class UpdateWidget(Form):
    name = StringField('Widget Name', validators=[validators.Length(max=25)])
    price = DecimalField('Widget Price', validators=[validators.NumberRange(min=4.4)])

    class Meta:
        name = "Barney"
        action = "lol"


@my_resolver.resolver('Query')
async def getUpdateWidgetForm(source, info, args):
    print(args)
    # widget = await info.context.WidgetDatasource.fetch(widgetId)
    # use your custom wtform like normal
    update_form = info.context.UpdateWidget.form(name='frank')
    return update_form


class DummyPostData(dict):

    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v


@my_resolver.resolver('Mutation')
async def postUpdateWidgetForm(source, info, args, form=None):
    print(f'MUTATE: {form}')
    update_form = info.context.UpdateWidget.form(form)
    if not update_form.validate():
        # ERROR!!
        raise GraphQLError("Update Widget Error", extensions=update_form.errors)

    return update_form


api = cannula.API(__name__)
api.register_resolver(my_resolver)
api.register_resolver(my_other_resolver)


results = api.call_sync(
    my_resolver.get_form_query('UpdateWidget', id='1234'),
    request=None,
)
print('DATA:')
pprint.pprint(results.data, compact=True, width=200)
print('ERRORS:')
pprint.pprint(results.errors)


results = api.call_sync(
    my_resolver.get_form_mutation('UpdateWidget', id='1234'),
    variables={'form': forms.FormDataWrapper(DummyPostData(name='darny', price=5.0))},
    request=None,
)
print(results)
