"""
Code generation for context.py
----------------

This module generates the context.py file which sets up datasources for each
database-backed type in the schema.
"""

import ast
from typing import List

from graphql import GraphQLObjectType
from cannula.codegen.base import (
    ast_for_annotation_assignment,
    ast_for_import_from,
    ast_for_name,
)
from cannula.codegen.schema_analyzer import CodeGenerator, TypeInfo
from cannula.format import format_code


class ContextGenerator(CodeGenerator):
    """Generates context.py with datasources for database-backed types"""

    def get_db_types(self) -> List[TypeInfo[GraphQLObjectType]]:
        """Get all types that have db_table metadata"""
        return [
            type_info
            for type_info in self.analyzer.object_types
            if type_info.is_db_type
        ]

    def create_datasource_class(
        self, type_info: TypeInfo[GraphQLObjectType]
    ) -> ast.ClassDef:
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

        # If no custom methods were added, add pass
        if not body:
            body.append(ast.Pass())

        return ast.ClassDef(
            name=datasource_name,
            bases=[base],
            keywords=keywords,
            body=body,
            decorator_list=[],
            type_params=[],
        )

    def create_context_class(
        self, db_types: List[TypeInfo[GraphQLObjectType]]
    ) -> ast.ClassDef:
        """Create the main Context class"""
        # Create __init__ method
        init_body: List[ast.stmt] = []
        # Create type annotations for each datasource
        annotations: List[ast.stmt] = []

        # Add datasource instantiations
        for type_info in db_types:
            graph_type = type_info.py_type
            datasource_name = f"{graph_type}Datasource"
            attr_name = f"{graph_type.lower()}s"

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
            type_params=[],
        )

        return ast.ClassDef(
            name="Context",
            bases=[ast_for_name("BaseContext")],
            keywords=[],
            body=[*annotations, init_method],
            decorator_list=[],
            type_params=[],
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
