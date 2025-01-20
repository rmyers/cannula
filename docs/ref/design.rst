Developer Guide
===============

This guide explains how the Cannula code generation system works internally for developers who want to modify or extend the code generation capabilities.

Architecture Overview
---------------------

The code generation system consists of several key components:

1. **Schema Analysis Layer** (`schema_analyzer.py`)
    * Processes GraphQL schema and metadata
    * Creates intermediate representations
    * Handles relationships and forward references

2. **Code Generation Layer**
    * Base `CodeGenerator` class
    * Specialized generators for different outputs:
        #. `PythonCodeGenerator` for type definitions
        #. `SQLAlchemyGenerator` for database models
        #. `ContextGenerator` for data source classes

3. **Parsing Layer**
    * `parse_type.py` - GraphQL type parsing
    * `parse_args.py` - Argument parsing

Data Flow
---------

.. code-block::

    GraphQL Schema + Metadata
            ↓
    SchemaAnalyzer
            ↓
    ObjectTypes, Fields, etc.
            ↓
    CodeGenerators
            ↓
    AST Generation
            ↓
    Final Code

Schema Analysis
---------------

The `SchemaAnalyzer` class is the entry point for processing schemas:

.. code-block:: python

    class SchemaAnalyzer:
        def __init__(self, schema: GraphQLSchema):
            self.schema = schema
            self.extensions = SchemaExtension(schema)
            self._analyze()

Key responsibilities:

* Categorizing types (objects, interfaces, unions, etc.)
* Processing metadata
* Handling relationships and forward references
* Creating intermediate representations

Type System
-----------

The system uses several intermediate representations:

1. **ObjectType**
    * Represents GraphQL object types
    * Holds fields and metadata
    * Tracks relationships

2. **Field**
    * Represents GraphQL fields
    * Contains type information
    * Holds arguments and metadata

3. **FieldType**
    * Represents field types
    * Handles lists and nullability
    * Manages type references

Code Generation Base
--------------------

The `CodeGenerator` base class provides common functionality:

.. code-block:: python

    class CodeGenerator(ABC):
        def __init__(self, analyzer: SchemaAnalyzer):
            self.analyzer = analyzer
            self.schema = analyzer.schema
            self.imports = analyzer.extensions.imports

        @abstractmethod
        def generate(self, *args, **kwargs) -> str:
            pass

Key features:

* Import management
* Access to analyzed schema
* AST generation helpers

AST Generation
--------------

Code generators create Python AST nodes which are then formatted into code. Common patterns:

1. **Class Generation**

.. code-block:: python

    ast.ClassDef(
        name=type_info.py_type,
        bases=[ast_for_name("BaseModel")],
        keywords=[],
        body=body,
        decorator_list=decorators,
    )

2. **Field Generation**

.. code-block:: python

    ast_for_annotation_assignment(
        self.name,
        annotation=ast_for_name(self.type),
        default=default
    )

Extending the System
--------------------

To add new code generation capabilities:

1. **New Generator**

   Create a new subclass of `CodeGenerator`:

   .. code-block:: python

    class MyGenerator(CodeGenerator):
        def generate(self) -> str:
            body: List[ast.stmt] = []
            # Add AST nodes to body
            module = self.create_module(body)
            return format_code(module)

2. **New Metadata**

   Add handling in `SchemaExtension`:

   .. code-block:: python

    class SchemaExtension:
        def __init__(self, schema: GraphQLSchema):
            self._my_metadata = schema.extensions.get("my_metadata", {})

3. **New Type Categories**

   Extend `SchemaAnalyzer`:

   .. code-block:: python

    class SchemaAnalyzer:
        def _analyze(self):
            self.my_types: List[MyType] = []
            # Process types...

Best Practices
--------------

1. **Type Handling**
    * Always use `parse_graphql_type` for type processing
    * Handle nullability consistently
    * Consider forward references

2. **Metadata Processing**
    * Validate metadata early
    * Provide clear error messages
    * Handle missing metadata gracefully

3. **AST Generation**
    * Use utility functions in `utils.py`
    * Keep AST construction clean and organized
    * Handle imports carefully

4. **Testing**
    * Add tests in `test_codegen.py`
    * Test edge cases and error conditions
    * Verify generated code validity

Common Tasks
------------

1. **Adding a New Field Metadata Option**

.. code-block:: python

    # In SchemaAnalyzer
    def get_field(self, field_name: str, ...):
        metadata = extensions.get_field_metadata(...)
        # Handle new metadata
        new_option = metadata.get("new_option")

    # In Generator
    def create_field_definition(self, field: Field):
        if new_option := field.metadata.get("new_option"):
            # Generate appropriate AST

2. **Adding a New Type Category**

.. code-block:: python

    # Create type class
    @dataclasses.dataclass
    class NewType:
        name: str
        # ...

    # Add to SchemaAnalyzer
    def _analyze(self):
        self.new_types: List[NewType] = []
        for name, type_def in self.schema.type_map.items():
            if is_new_type(type_def):
                self.new_types.append(self.parse_new_type(type_def))

3. **Modifying Code Generation**

.. code-block:: python

    class MyGenerator(CodeGenerator):
        def render_object_type(self, type_info: ObjectType):
            # Custom AST generation
            return [
                ast.ClassDef(
                    name=type_info.py_type,
                    # ...
                )
            ]

Error Handling
--------------

The system uses custom exceptions for schema validation:

.. code-block:: python

    class SchemaValidationError(Exception):
        """Raised when schema validation fails"""
        pass

Key validation points:

* Field nullability conflicts
* Invalid relationships
* Missing required metadata
* Type reference issues

Development Workflow
--------------------

1. Make changes to code generation
2. Run tests: `make test`
3. Generate sample code to verify changes
4. Update documentation if needed
5. Add new tests for changes

Contributing
------------

When contributing changes:

1. Follow the existing code style
2. Add appropriate tests
3. Update documentation
4. Handle edge cases
5. Consider backward compatibility

Further Reading
---------------

* GraphQL AST documentation
* Python AST module documentation
* SQLAlchemy relationship documentation
* Pydantic model documentation