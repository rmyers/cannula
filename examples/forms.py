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


def is_42(form, field):
    if field.data != 42:
        raise validators.ValidationError('Must be 42')


class Other(Form):
    name = StringField('Widget Namer', validators=[validators.Length(max=25), is_42])

    class Meta:
        name = 'Frank'


class UpdateWidget(Form):
    name = StringField('Widget Name', validators=[validators.Length(max=25), is_42])
    price = DecimalField('Widget Price', validators=[validators.NumberRange(min=4.0)])
    fool = SelectMultipleField('What', choices=[('foo', 'bar')])
    other = FormField(Other)
    listy = FieldList(StringField('Name', [validators.required()], default='Jane'), max_entries=34, min_entries=2)
    booly = BooleanField('slkjl', default=False)

    class Meta:
        name = "Barney"


api = cannula.API(__name__)

# Add the wtforms_resolver to your registered resolvers
api.register_resolver(forms.wtforms_resolver)

# Add in your custom resolver to get the form with data
my_resolver = cannula.Resolver(__name__, schema='''
    type Widget {
        name: String
    }
    extend type Query {
        getUpdateWidgetForm(widgetId: String!): WTForm
    }
    extend type Mutation {
        updateWidget(form: String): Widget
    }
''')


@my_resolver.resolver('Query')
async def getUpdateWidgetForm(source, info, widgetId):
    # widget = await info.context.WidgetDatasource.fetch(widgetId)
    # use your custom wtform like normal
    update_form = UpdateWidget()
    return update_form


class DummyPostData(dict):

    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v


@my_resolver.resolver('Mutation')
async def updateWidget(source, info, form=None):
    print(f'MUTATE: {form}')
    form_data = urllib.parse.parse_qs(form)
    update_form = UpdateWidget(DummyPostData(**form_data))
    if not update_form.validate():
        # ERROR!!
        raise GraphQLError("Update Widget Error", extensions=update_form.errors)
    return update_form


api.register_resolver(my_resolver)


UPDATE_WIDGET_QUERY = forms.parse_form_query('''
    query getForm($widgetId: String!) {
        getUpdateWidgetForm(widgetId: $widgetId) {
            ...formQueryFragment
        }
    }
''')

UPDATE_WIDGET_MUTATION = parse('''
    mutation widgetUpdate($form: String!) {
        updateWidget(form: $form) {
            name
        }
    }
''')


results = api.call_sync(
    UPDATE_WIDGET_QUERY,
    variables={'widgetId': '2345'},
    request=None,
)
print('DATA:')
pprint.pprint(results.data, compact=True, width=200)
print('ERRORS:')
pprint.pprint(results.errors)

payload = urllib.parse.urlencode(
    [
        ('name', 'Darla'),
        ('price', '1.4'),
    ]
)

posted = api.call_sync(
    UPDATE_WIDGET_MUTATION,
    variables={'form': payload},
    request=None
)

print(posted)
