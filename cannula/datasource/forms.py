"""
WTForms Data Source
-------------------

This class will assist in making dynamically generated forms and validation
on your front end. It requires that you have the wtforms library installed.

The main use case is to define your forms and validation in a single class
then use GraphQL to expose the fields in a way that is easy to update.

Here is a simple example::

    import cannula
    from cannula.datasource import forms
    from wtforms import Form, Length, StringField, DecimalField

    class UpdateWidget(Form):
        name = StringField('Widget Name', validators=[Length(max=25)])
        price = DecimalField('Widget Price', validators=[NumberRange(min=4.0)])

    api = cannula.API(__name__)

    # Add the wtforms_resolver to your registered resolvers
    api.register_resolver(forms.wtforms_resolver)

    # Add in your custom resolver to get the form with data
    my_resolver = cannula.resolver(None, schema='''
        extend type Query {
            getUpdateWidgetForm(widgetId: String!) WTForm
        }
        extend type Mutation {
            updateWidget(widgetId: String!, form: WTForm) WTForm
        }
    ''')

    @my_resolver.resolve('Query')
    async def getUpdateWidgetForm(source, info, widgetId):
        widget = await info.context.WidgetDatasource.fetch(widgetId)
        # use your custom wtform like normal
        update_form = UpdateWidget(obj=widget)
        return update_form

    @my_resolver.resolve('Mutation')
    async def updateWidget(source, info, widgetId, form=None):
        widget = await info.context.WidgetDatasource.fetch(widgetId)
        if form.validate():
            # Update the Widget
            widget.save()
        return update_form


    api.register_resolver(my_resolver)


Now you can serialize this form and send that to your front end for rendering,
you can use the `parse_form_query` that adds the formQueryFragment and parses
the results to a query document::

    UPDATE_WIDGET_QUERY = forms.parse_form_query('''
        query getForm($widgetId: String!) {
            getUpdateWidgetForm(widgetId: $widgetId) {
                ...formQueryFragment
            }
        }
    ''')

    @route('/widget/<widget_id:str>/update')
    def update_widget(widget_id):
        API.call_sync(
            UPDATE_WIDGET_QUERY,
            variables={'widgetId': widget_id},
            request=request
        )
"""

import inspect

from graphql import parse
try:
    import wtforms
    from wtforms.widgets import html5
except ImportError:
    raise Exception('You must install wtforms to use this module')

from cannula.api import Resolver


WTFORMS_SCHEMA = '''
# WTFORMS_SCHEMA
# --------------
#
# This is the base schema for wtforms, it represents a generic mapping of
# form fields, validators, and errors.


union WTField = WTFormField | WTFieldList | WTFBaseField

"Represents a JSON field to allow arbitrary key/value pairs"
scalar WTFJSON

"""
This holds the class name of the validator (Length, Required, etc) and the
arguments that are set on the object.
"""
type WTFormsValidator {
    name: String
    arguments: WTFJSON
}

type WTFormsValidationError {
    fieldName: String
    errors: [String]
}

"""
Widgets define how the form fields should appear. The base input types are well
defined. On the UI side these will need to be implemented but these widgets
should hopefully contain enough information to render them.
"""
union WTFWidget = WTFCustomWidget | WTFInputWidget | WTFSelectWidget

"""
This represents a custom UI widget that is used to render the field. The
attributes are a JSON field as this is a custom widget type and we don't
know those until we parse it.
"""
type WTFCustomWidget {
    name: String!
    attributes: WTFJSON
}

type WTFInputWidget {
    name: String!
    type: String!
}


type WTFSelectWidget {
    name: String!
    multiple: Boolean
}

"Encapsulate an ordered list of multiple instances of the same field type, keeping data as a list."
type WTFieldList {
    name: String!
    label: String

    entries: [WTField]

    "Always have at least this many entries on the field."
    min_entries: Int
    "Accept no more than this many entries as input."
    max_entries: Int

    "Flags are simple attributes like 'required' that should be applied to the field."
    flags: [String]

    "Any error messages that should be displayed."
    errors: [String]
}


type WTFormField {
    name: String!
    label: String
    fields: [WTField]
}

type WTFOption {
    value: String!
    label: String!
    selected: Boolean
}

type WTFBaseField {
    name: String!
    label: String
    description: String
    widget: WTFWidget

    "The current value of the field."
    data: String
    options: [WTFOption]

    "Flags are simple attributes like 'required' that should be applied to the field."
    flags: [String]

    "Any error messages that should be displayed."
    errors: [String]
}

type WTForm {
    action: String
    method: String
    fields: [WTField]
    errors: [String]
}
'''

FORM_QUERY_FRAGMENT = '''
fragment formQueryFragment on WTForm {
    action
    method
    fields {
        __typename
        ... on WTFormField {
            ...formFieldQuery
        }
        ... on WTFieldList {
            ...fieldListQuery
        }
        ... on WTFBaseField {
            ...baseFieldQuery
        }
    }
}

fragment fieldListQuery on WTFieldList {
    name
    label
    entries {
        __typename
        ... on WTFBaseField {
            ...baseFieldQuery
        }
        ... on WTFormField {
            name
            label
            fields {
                __typename
                ... on WTFBaseField {
                    ...baseFieldQuery
                }
            }
        }
    }
    min_entries
    max_entries
}

fragment formFieldQuery on WTFormField {
    name
    label
    fields {
        __typename
        ... on WTFieldList {
            ...fieldListQuery
        }
        ... on WTFBaseField {
            ...baseFieldQuery
        }
    }
}

fragment baseFieldQuery on WTFBaseField {
    name
    label
    description
    widget {
        __typename
        ... on WTFInputWidget {
            name
            type
        }
        ... on WTFSelectWidget {
            name
            multiple
        }
        ... on WTFCustomWidget {
            name
            attributes
        }
    }
    options {
        value
        label
        selected
    }
    data
    errors
}
'''


class ValidatorWrapper:

    def __init__(self, validator):
        self._validator = validator

    @property
    def attributes(self):
        attrs = {}
        for key, value in self._validator.__dict__.items():
            _type = type(value).__name__
            if _type == 'SRE_Pattern':
                attrs[key] = value.pattern
            elif _type in ['int', 'str', 'bool', 'float']:
                attrs[key] = value
            else:
                attrs[key] = str(value)

        return attrs


class WidgetWrapper:

    def __init__(self, widget):
        self._widget = widget

    @property
    def __typename__(self):
        if isinstance(self._widget, (html5.NumberInput, html5.RangeInput)):
            return 'WTFNumberWidget'
        elif isinstance(self._widget, wtforms.widgets.Input):
            return 'WTFInputWidget'
        elif isinstance(self._widget, wtforms.widgets.Select):
            return 'WTFSelectWidget'
        print(f'Custom WIDGET? name: {self.name}')
        return 'WTFCustomWidget'

    @property
    def type(self):
        return self._widget.input_type

    @property
    def name(self):
        return type(self._widget).__name__

    @property
    def checked(self):
        return self._widget.checked


class OptionWrapper:

    def __init__(self, value, label, selected):
        self.value = value
        self.label = label
        self.selected = selected


class FieldWrapper:

    def __init__(self, field):
        self._field = field
        print(field.type)

    @property
    def __typename__(self):
        if self._field.type == 'FieldList':
            return 'WTFieldList'
        elif self._field.type == 'FormField':
            return 'WTFormField'
        return 'WTFBaseField'

    @property
    def validators(self):
        for val in self._field.validators:
            if inspect.isfunction(val):
                print(val.__name__)
            else:
                print(val.__class__.__name__)
                print(dir(val))
                for k, v in val.__dict__.items():
                    print(f'{k}:{v}')
                    print(type(v))

    @property
    def name(self):
        return self._field.name

    @property
    def label(self):
        return self._field.label.text

    @property
    def description(self):
        return self._field.description

    @property
    def errors(self):
        return self._field.errors

    @property
    def widget(self):
        return WidgetWrapper(self._field.widget)

    @property
    def validators(self):
        for validator in self._field.validators:
            yield ValidatorWrapper(validator)

    @property
    def fields(self):
        """Used by WTFormField to return subform fields."""
        for field in self._field.form:
            yield FieldWrapper(field)

    @property
    def data(self):
        return self._field.data

    @property
    def entries(self):
        """Used by WTFieldList to return subfields."""
        for field in self._field:
            yield FieldWrapper(field)

    @property
    def max_entries(self):
        return self._field.max_entries

    @property
    def min_entries(self):
        return self._field.min_entries

    @property
    def inputType(self):
        print(dir(self.widget))
        return self.widget.input_type

    @property
    def options(self):
        if not hasattr(self._field, 'iter_choices'):
            return
        for value, label, selected in self._field.iter_choices():
            yield OptionWrapper(value, label, selected)


def parse_form_query(query_doc):
    return parse(query_doc + FORM_QUERY_FRAGMENT)


# This is the main resolver that you can use to simplify your wtforms.
wtforms_resolver = Resolver(name='WTForms', schema=WTFORMS_SCHEMA)


@wtforms_resolver.resolver('WTForm')
async def action(form, info):
    """Resolves the fields on a wtform object."""
    return '/foo'


@wtforms_resolver.resolver('WTForm')
async def fields(form, info):
    """Resolves the fields on a wtform object."""
    return [FieldWrapper(field) for field in form]
