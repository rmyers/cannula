from cannula.utils import gql

DB_SQL = gql(
    """
    "This directive marks a type as a database table."
    directive @db_sql(
        "By default the table name will be the plural lowercase name."
        table_name: String,

        "Allow multiple fields to be marked as primary_key."
        composite_primary_key: Boolean = False,

        "Database constraints to apply."
        constraint: [String]
    ) on OBJECT
    """
)

FIELD_META = gql(
    '''
    """
    This directive holds values to define how a field is configured on the parent or related type.

    Since fields can be either a simple attribute on the parent or a complex resolver the context
    matters. To simplify things we have combined all the concepts into this directive. For instance
    you may have a field that is defined on a type that is a database table but preforms an api
    call to fetch data on a related resolver. It would be hard to keep straight if you had to put
    each different value in a different directive definition.
    """
    directive @field_meta(
        "Override the name used for the database column"
        db_column: String,

        "Mark this field as the primary_key"
        primary_key: Boolean = False,

        "Foreign Key relation for this column"
        foreign_key: String,

        "Index this column"
        index: Boolean = False,

        "Mark the column as nullable"
        nullable: Boolean = False,

        "Mark the column as unique"
        unique: Boolean = False,

        """
        Optional where clause to perform, should use proper
        sqlalchemy text query syntax like:

            where: "user_id = :id AND date < :time"
        """
        where: String,

        """
        Optional Raw SQL to run:

            "SELECT name, text FROM projects WHERE text LIKE :search ORDER BY name"
        """
        raw_sql: String,

        """
        Attributes from the parent to include aka 'self.id' in
        queries in addition to schema arguments. (see 'where' and 'raw_sql')
        """
        args: [String],

        "Resolver function to call using dotted notation 'package.module:func_name'"
        function: String

        "Assign a value to indicate the complexity of this field to limit query size"
        weight: Float,
    ) on FIELD_DEFINITION
    '''
)

# These Directives match the ones in Apollo Graph for the 'connectors'
# https://www.apollographql.com/docs/graphos/schema-design/connectors
CONNECT = gql(
    '''
    directive @connect(
        """
        Optionally references reusable configuration, corresponding
        to `@source(name: $source)`
        """
        source: String

        "HTTP configuration"
        http: ConnectHTTP!

        "Used to map an API's JSON response to GraphQL fields"
        selection: JSONSelection!

        """
        Allowed only on fields of `Query`. If set to
        `true` the field acts as an entity resolver
        in Apollo Federation
        """
        entity: Boolean
    ) repeatable on FIELD_DEFINITION

    "Only one of {GET,POST,PUT,PATCH,DELETE} is allowed"
    input ConnectHTTP {
        GET: URLPathTemplate
        POST: URLPathTemplate
        PUT: URLPathTemplate
        PATCH: URLPathTemplate
        DELETE: URLPathTemplate

        """
        Header mappings for propagating headers from the
        original client request to the GraphOS Router, or injecting
        specific values.
        """
        headers: [HTTPHeaderMapping!]

        "Mapping from field arguments to POST|PUT|PATCH request bodies"
        body: JSONSelection
    }

    directive @source(
        """
        Unique identifier for the API this directive
        represents, for example "productsv1"
        """
        name: String!

        "HTTP configuration"
        http: SourceHTTP!
    ) repeatable on SCHEMA

    input SourceHTTP {
        """
        The base scheme, hostname, and path to use,
        like "https://api.example.com/v2"
        """
        baseURL: String!

        """
        Default header mappings used for all related
        connectors. If a connector specifies its own
        header mappings, that list is merged with this
        one, with the connector's mappings taking precedence
        when the `name` value matches.
        """
        headers: [HTTPHeaderMapping!]
    }

    """
    Defines a header for an HTTP request and where its
    value comes from.

    Only one of {from, value} is allowed
    """
    input HTTPHeaderMapping {
        "The name of the header to send to HTTP APIs"
        name: String!

        """
        The name of the header in the original client
        request to the GraphOS Router
        """
        from: String

        "Optional hard-coded value for non-passthrough headers"
        value: String
    }

    """
    A URL path with optional parameters, mapping to GraphQL
    fields or arguments
    """
    scalar URLPathTemplate

    "A custom syntax for mapping JSON data to GraphQL schema"
    scalar JSONSelection
'''
)
