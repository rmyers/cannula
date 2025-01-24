"""
Code generation for context.py
----------------

This module generates the context.py file which sets up datasources for each
database-backed type in the schema.
"""

import ast
from typing import List, Optional

from cannula.codegen.schema_analyzer import CodeGenerator, ObjectType
from cannula.errors import SchemaValidationError
from cannula.format import format_code
from cannula.types import Field
from cannula.utils import (
    ast_for_annotation_assignment,
    ast_for_import_from,
    ast_for_name,
)


class ContextGenerator(CodeGenerator):
    """Generates context.py with datasources for database-backed types"""

    def create_relation_method(
        self,
        related_field: Field,
        where_clause: Optional[str] = None,
    ) -> ast.AsyncFunctionDef:
        """Create a method for fetching related objects"""
        args = [
            ast.arg(arg="self"),
            *[arg.as_ast for arg in related_field.related_args],
            *related_field.positional_args,
        ]

        # Use the correct class method for fetching single or list of items
        cls_method = "get_models" if related_field.field_type.is_list else "get_model"

        # Build the call args with the where clause or include all results
        call_args: list[ast.expr] = [
            ast.Call(func=ast_for_name("true"), args=[], keywords=[])
        ]
        if where_clause:
            call_args = [
                ast.Call(
                    func=ast_for_name("text"),
                    args=[ast.Constant(where_clause)],
                    keywords=[],
                )
            ]

        method_body: list[ast.stmt] = [
            ast.Return(
                value=ast.Await(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="self", ctx=ast.Load()),
                            attr=cls_method,
                            ctx=ast.Load(),
                        ),
                        args=call_args,
                        keywords=related_field.related_keywords,
                    )
                )
            )
        ]

        return ast.AsyncFunctionDef(
            name=related_field.relation_method,
            args=ast.arguments(
                posonlyargs=[],
                args=args,
                kwonlyargs=[*related_field.kwonlyargs],
                kw_defaults=related_field.kwdefaults,
                defaults=[],
                vararg=None,
                kwarg=None,
            ),
            body=method_body,
            decorator_list=[],
            returns=ast_for_name(related_field.type),
            type_params=[],  # type: ignore
        )

    def create_datasource_class(self, type_info: ObjectType) -> ast.ClassDef:
        """Create a datasource class for a specific type"""
        # Get the type names
        graph_type = type_info.py_type
        db_type = type_info.db_type
        datasource_name = f"{graph_type}Datasource"

        # Create the base class with generics
        base = ast.Subscript(
            value=ast_for_name("DatabaseRepository"),
            slice=ast.Tuple(
                elts=[ast_for_name(db_type), ast_for_name(graph_type)], ctx=ast.Load()
            ),
            ctx=ast.Load(),
        )

        # Add the graph_model and db_model class arguments
        keywords = [
            ast.keyword(arg="graph_model", value=ast_for_name(graph_type)),
            ast.keyword(arg="db_model", value=ast_for_name(db_type)),
        ]

        # Create the datasource class
        body: List[ast.stmt] = []

        for related_field in type_info.related_fields:
            # If the related field has a fk_field the generated type object
            # will use that to construct `get_model_by_pk` and we don't need
            # a special resolver function in that case.
            if related_field.fk_field is not None:
                continue

            where_clause = related_field.metadata.where
            if not where_clause and not related_field.field_type.is_list:
                raise SchemaValidationError(
                    f"{related_field} includes a relation to {type_info.name} that requires "
                    "a 'where' metadata attribute like 'user_id = :id' to preform the query."
                )

            body.append(
                self.create_relation_method(
                    related_field=related_field, where_clause=where_clause
                )
            )

        # If no custom methods were added, add pass
        if not body:
            body.append(ast.Pass())

        return ast.ClassDef(
            name=datasource_name,
            bases=[base],
            keywords=keywords,
            body=body,
            decorator_list=[],
            type_params=[],  # type: ignore
        )

    def create_context_class(self, db_types: List[ObjectType]) -> ast.ClassDef:
        """Create the main Context class"""
        # Create __init__ method
        init_body: List[ast.stmt] = []
        # Create type annotations for each datasource
        annotations: List[ast.stmt] = []

        # Add datasource instantiations
        for type_info in db_types:
            graph_type = type_info.py_type
            datasource_name = f"{graph_type}Datasource"
            attr_name = type_info.context_attr

            annotations.append(
                ast_for_annotation_assignment(
                    attr_name, annotation=ast_for_name(datasource_name)
                )
            )
            init_body.append(
                ast.Assign(
                    targets=[
                        ast.Attribute(
                            value=ast_for_name("self"), attr=attr_name, ctx=ast.Store()
                        )
                    ],
                    value=ast.Call(
                        func=ast_for_name(datasource_name),
                        args=[ast_for_name("session_maker")],
                        keywords=[],
                    ),
                )
            )

        # Create the __init__ method
        init_method = ast.FunctionDef(
            name="__init__",
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="self"),
                    ast.arg(
                        arg="session_maker",
                        annotation=ast_for_name("async_sessionmaker"),
                    ),
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
                vararg=None,
                kwarg=None,
            ),
            body=init_body,
            decorator_list=[],
            returns=None,
            type_params=[],  # type: ignore
        )

        return ast.ClassDef(
            name="Context",
            bases=[ast_for_name("BaseContext")],
            keywords=[],
            body=[*annotations, init_method],
            decorator_list=[],
            type_params=[],  # type: ignore
        )

    def generate(self) -> str:
        """Generate the complete context.py file"""
        db_types = self.get_db_types()
        if not db_types:
            return ""

        body: List[ast.stmt] = []

        model_types = {type_info.py_type for type_info in self.analyzer.object_types}
        db_model_types = {type_info.db_type for type_info in db_types}
        # Add required imports
        body.extend(
            [
                ast_for_import_from(".sql", db_model_types),
                ast_for_import_from(".types", model_types),
            ]
        )

        # Create datasource classes
        for type_info in db_types:
            datasource = self.create_datasource_class(type_info)
            body.append(datasource)

        # Add context class
        context = self.create_context_class(db_types)
        body.append(context)

        # Create and format the complete module
        module = self.create_module(body)

        return format_code(module)
