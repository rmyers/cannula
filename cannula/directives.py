from cannula.utils import gql

DB_SQL = gql(
    '''
    """
    This directive marks a type as a database table.

    Args:
        table_name (String): By default the table name will be the plural lowercase name.
        composite_primary_key (Boolean = False): Allow multiple fields to be marked as primary_key.
        constraint ([String]): Database constraints to apply
    """
    directive @db_sql(
        table_name: String,
        composite_primary_key: Boolean = False,
        constraint: [String]
    ) on OBJECT
    '''
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

    Args:
        db_column (String): Override the name used for the database column
        primary_key (Boolean = False): Mark this field as the primary_key
        foreign_key (String): Foreign Key relation for this column
        index (Boolean = False): Index this column
        nullable (Boolean = False): Mark the column as nullable
        unique (Boolean = False): Mark field as unique
        where (String): Optional where clause 'user_id = :id AND date < :time'
        raw_sql (String): Raw SQL to run 'SELECT name, text FROM projects WHERE text LIKE :search ORDER BY name'
        args ([String]): Attributes from the parent to include aka 'self.id' in queries in addition to schema arguments.
        function (String): Resolver function to call using dotted notation 'package.module:func_name'
        weight (Float): Assign a value to indicate the complexity of this field to limit query size

    """
    directive @field_meta(
        db_column: String,
        primary_key: Boolean = False,
        foreign_key: String,
        index: Boolean = False,
        nullable: Boolean = False,
        unique: Boolean = False,
        where: String,
        raw_sql: String,
        args: [String],
        weight: Float,
    ) on FIELD_DEFINITION
    '''
)
