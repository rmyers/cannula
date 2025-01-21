.. _codegen:

Code Generation
===============


The ``cannula codegen`` command generates Python code from your GraphQL schema. It creates type definitions, SQLAlchemy models, and context classes based on your schema and metadata.

See the tutorial for an example :doc:`../tutorial/part3`

Configuration
-------------

By default, the command looks for a ``pyproject.toml`` file in the current directory. Here's a sample configuration:

.. code-block:: toml

    [tool.cannula.codegen]
    schema = "schema/"  # Directory containing .graphql files
    output = "generated/"  # Output directory for generated code
    use_pydantic = false  # Use pydantic models instead of dataclasses

Schema Metadata
---------------

You can add metadata to your GraphQL schema using descriptions and directives. Here are the supported options:

Type Metadata
~~~~~~~~~~~~~

Add metadata to types using descriptions with YAML frontmatter:

.. code-block:: graphql

    """
    User type
    ---
    metadata:
        db_table: users  # SQLAlchemy table name
        cache: false     # Disable caching for this type
        ttl: 0          # Cache TTL
        weight: 1.2     # Custom metadata
    """
    type User {
        id: ID!
        name: String!
    }

Field Metadata
~~~~~~~~~~~~~~

Add metadata to fields using directives or descriptions:

.. code-block:: graphql

    type User {
        "User ID @metadata(primary_key: true)"
        id: ID!

        "@metadata(index: true)"
        name: String!

        "@metadata(db_column: email_address, unique: true)"
        email: String!

        "@metadata(nullable: true)"
        age: Int

        """
        User's projects
        ---
        metadata:
            where: "author_id = :id"
            args: id
        """
        projects(limit: Int = 10): [Project]
    }

Supported Field Metadata
~~~~~~~~~~~~~~~~~~~~~~~~

* ``primary_key: bool`` - Mark field as primary key
* ``foreign_key: str`` - Reference another table (e.g., "users.id")
* ``index: bool`` - Create an index on this column
* ``unique: bool`` - Add unique constraint
* ``nullable: bool`` - Allow NULL values
* ``db_column: str`` - Custom column name
* ``where: str`` - SQL WHERE clause for relations
* ``args: str | list[str]`` - Arguments to pass to relation query
* ``relation: dict`` - SQLAlchemy relationship options

Relationships
~~~~~~~~~~~~~

Define relationships between types:

.. code-block:: graphql

    type User {
        id: ID!
        "@metadata(foreign_key: projects.id)"
        project_id: String!

        """
        User's project
        ---
        metadata:
            relation:
                back_populates: "author"
                cascade: "all, delete-orphan"
        """
        project: Project!
    }

Generated Code
--------------

The command generates three files:

* ``types.py`` - Python type definitions
* ``sql.py`` - SQLAlchemy models
* ``context.py`` - Context classes with data sources

Example
-------

Here's a complete example:

.. code-block:: graphql

    """
    User in the system
    ---
    metadata:
        db_table: users
    """
    type User {
        "User ID @metadata(primary_key: true)"
        id: ID!

        "@metadata(index: true)"
        name: String!

        "@metadata(db_column: email_address, unique: true)"
        email: String!

        """
        User's projects
        ---
        metadata:
            where: "author_id = :id"
            args: id
        """
        projects: [Project]
    }

    """
    Project type
    ---
    metadata:
        db_table: projects
    """
    type Project {
        "Project ID @metadata(primary_key: true)"
        id: ID!
        name: String!
        "@metadata(foreign_key: users.id)"
        author_id: ID!
        author: User!
    }

This will generate:

* SQLAlchemy models with proper relationships
* Python types with computed fields
* A context class with User and Project datasources

Relationship Queries
--------------------

When defining relationships between types, you can specify how to fetch related data using ``where`` clauses and arguments. This is especially useful for filtering relationships and optimizing queries.

Where Clauses
~~~~~~~~~~~~~

The ``where`` clause in metadata defines the SQL condition for fetching related data. It uses SQLAlchemy text syntax with named parameters:

.. code-block:: yaml

    ---
    metadata:
        where: "author_id = :id"
        args: id


Arguments
~~~~~~~~~

There are two types of arguments you can use in relationship queries:

1. Metadata Arguments (``args``)
   These reference fields from the parent type that are passed to the where clause:

   .. code-block:: graphql

       type User {
           id: ID!
           org_id: ID!
           """
           Projects in user's organization
           ---
           metadata:
               where: "org_id = :org_id AND author_id = :id"
               args: [id, org_id]
           """
           projects: [Project]
       }

2. Field Arguments
   These are regular GraphQL arguments that can be used in queries:

   .. code-block:: graphql

       type User {
           id: ID!
           """
           User's projects with filtering
           ---
           metadata:
               where: "author_id = :id AND is_active = :active"
               args: id
           """
           projects(active: Boolean = true): [Project]
       }

Combining Arguments
~~~~~~~~~~~~~~~~~~~

You can combine both types of arguments:

.. code-block:: graphql

    type User {
        id: ID!
        org_id: ID!
        """
        Filtered projects
        ---
        metadata:
            where: "org_id = :org_id AND author_id = :id AND created_at > :since"
            args: [id, org_id]
        """
        projects(since: DateTime!): [Project]
    }

In this example:
- ``id`` and ``org_id`` come from the User object
- ``since`` comes from the GraphQL query argument

Query Example:

.. code-block:: graphql

    query {
        user {
            id
            # Fetches projects where:
            # org_id = user.org_id AND
            # author_id = user.id AND
            # created_at > '2024-01-01'
            projects(since: "2024-01-01") {
                name
            }
        }
    }

Default Values
~~~~~~~~~~~~~~

Field arguments can have default values:

.. code-block:: graphql

    type User {
        id: ID!
        """
        Active projects by default
        ---
        metadata:
            where: "author_id = :id AND is_active = :active"
            args: id
        """
        projects(active: Boolean = true): [Project]
    }

Query Optimization
~~~~~~~~~~~~~~~~~~

The relationship query system helps optimize database queries by:

1. Only fetching related data when requested in the GraphQL query
2. Applying filters at the database level
3. Using parent object fields efficiently in relationship queries
4. Supporting default filters via field argument defaults


Running
-------

Generate code by running::

    $ cannula codegen

Options:

* ``--schema PATH`` - Schema directory (overrides pyproject.toml)
* ``--output PATH`` - Output directory (overrides pyproject.toml)
* ``--use-pydantic`` - Use pydantic models
* ``--dry-run`` - Print output without writing files