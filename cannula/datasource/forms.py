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
"""

import typing

from graphql import parse, concat_ast

try:
    import wtforms
    from wtforms.widgets import html5
except ImportError:
    raise Exception('You must install wtforms to use this module')

from ..api import Resolver
from ..utils import gql


WTFORMS_SCHEMA = gql('''
# WTFORMS_SCHEMA
# --------------
#
# This is the base schema for wtforms, it represents a generic mapping of
# form fields, validators, and errors.


union WTField = WTFormField | WTFieldList | WTFBaseField

"""
Represents a JSON field to allow arbitrary key/value pairs.
"""
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

"""
Encapsulate an ordered list of multiple instances of the same field type, keeping data as a list.
"""
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

"""
Input arguments used to pass arguments to the resolver function.
"""
input WTFormQueryArgs {
    key: String
    value: String
}
''')

FORM_QUERY_FRAGMENT = gql('''
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
''')


class Wrapper:
    """Wrap an object with extra functionality"""

    wrapped_name = '_obj'

    def __init__(self, obj):
        setattr(self, self.wrapped_name, obj)

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        obj = getattr(self, self.wrapped_name)
        return getattr(obj, attr)


class ValidatorWrapper(Wrapper):

    wrapped_name = '_validator'

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


class WidgetWrapper(Wrapper):

    wrapped_name = '_widget'

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


class OptionWrapper:

    def __init__(self, value, label, selected):
        self.value = value
        self.label = label
        self.selected = selected


class FieldWrapper(Wrapper):

    wrapped_name = '_field'

    @property
    def __typename__(self):
        if self._field.type == 'FieldList':
            return 'WTFieldList'
        elif self._field.type == 'FormField':
            return 'WTFormField'
        return 'WTFBaseField'

    @property
    def label(self):
        return self._field.label.text

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
    def entries(self):
        """Used by WTFieldList to return subfields."""
        for field in self._field:
            yield FieldWrapper(field)

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


class FormDataWrapper(Wrapper):
    """Form Data Wrapper

    This is used to encapsulate the raw form data from a request to satisfy
    the input argument to the WTForm mutations.

    Usage::

        async def process_form(request):
            form = await request.form()
            results = api.call(
                my_resolver.get_form_mutation('MyForm'),
                variables={'form': FormDataWrapper(form)},
                request=request,
            )
    """

    def __contains__(self, name):
        return name in self._obj

    def decode(self, *args, **kwargs):
        return self


async def action(form, info, *args, **kwargs):
    """Resolves the fields on a wtform object."""
    # HMMM maybe this does not belong here.
    return '/foo'


async def fields(form, info):
    """Resolves the fields on a wtform object."""
    return [FieldWrapper(field) for field in form]


class WTFormsDataSource(typing.NamedTuple):
    """WTForms Data Source

    This wraps the underlining form which was registerd and provides access
    to the arguments that are needed by the resolver functions.
    """

    form: wtforms.Form
    args: typing.List[str]
    query_name: str
    mutation_name: str
    return_type: str
    return_fields: str
    context: typing.Any = None
    query_fragment: str = '...formQueryFragment'

    def __call__(self, context):
        return WTFormsDataSource(
            self.form,
            self.args,
            self.query_name,
            self.mutation_name,
            self.return_type,
            self.return_fields,
            context,
        )

    def _get_form_args(self, **kwargs):
        """Return a query list string of key/value pairs from kwargs"""
        args = [f'{{key: "{key}", value: "{value}"}}' for key, value in kwargs.items()]
        return ','.join(args)

    def get_query(self, **kwargs):
        form_args = []
        # Make sure all the arguments are available
        for arg in self.args:
            assert arg in kwargs, f'required argument {arg} missing!'
            form_args.append({'key': arg, 'value': kwargs[arg]})

        args_string = self._get_form_args(**kwargs)
        query = gql(f'''
            query form {{
                form: {self.query_name}(args: [{args_string}]) {{
                    {self.query_fragment}
                }}
            }}
        ''')
        return concat_ast([query, FORM_QUERY_FRAGMENT])

    def get_mutation(self, **kwargs):
        form_args = []
        # Make sure all the arguments are available
        for arg in self.args:
            assert arg in kwargs, f'required argument {arg} missing!'
            form_args.append({'key': arg, 'value': kwargs[arg]})

        args_string = self._get_form_args(**kwargs)

        needs_query_fragment = self.return_type == 'WTForm'

        return_fields = self.query_fragment if needs_query_fragment else self.return_fields

        query = gql(f'''
            mutation form($form: WTFJSON) {{
                form: {self.mutation_name}(args: [{args_string}], form: $form) {{
                    {return_fields}
                }}
            }}
        ''')
        return concat_ast([query, FORM_QUERY_FRAGMENT]) if needs_query_fragment else query


class WTFormsResolver(Resolver):

    base_schema = {
        'wtforms': WTFORMS_SCHEMA
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry['WTForm']['fields'] = fields
        self.registry['WTForm']['action'] = action

    def register_form(
        self,
        name: str = None,
        args: typing.List[str] = None,
        return_type: str = None,
        return_fields: str = None,
    ) -> typing.Any:
        if return_type is not None:
            assert return_fields, f'Must specify return_fields if you use a custom return_type'
        else:
            return_type = 'WTForm'

        def decorator(klass):
            arguments = args.copy()
            registry_name = name or klass.__name__
            query_name = f'get{registry_name}Form'
            mutation_name = f'post{registry_name}Form'

            FormDataSource = WTFormsDataSource(
                klass,
                arguments,
                query_name,
                mutation_name,
                return_type,
                return_fields,
            )

            self.datasources[registry_name] = FormDataSource
            self.forms[registry_name] = FormDataSource
            self._extend_schema(query_name, mutation_name, return_type)

            return klass
        return decorator

    def _extend_schema(self, query_name: str, mutation_name: str, return_type: str) -> None:
        extra_schema = gql(f'''
            extend type Query {{
                {query_name}(args: [WTFormQueryArgs]): WTForm
            }}
            extend type Mutation {{
                {mutation_name}(args: [WTFormQueryArgs], form: WTFJSON): {return_type}
            }}
        ''')

        if self._schema is not None:
            if isinstance(self._schema, str):
                self._schema = parse(self._schema)
            self._schema = concat_ast([self._schema, extra_schema])
            return

        self._schema = extra_schema


def unwrap_args(form_query_argument_list):
    """Turn the serialized key/value pairs back into a dict."""
    kwargs = {}
    for arg in form_query_argument_list:
        kwargs[arg['key']] = arg['value']
    return kwargs
