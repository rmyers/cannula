import ast
import logging
from typing import List, TypeVar, cast
from graphql import (
    GraphQLObjectType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
)

from cannula.format import format_code
from cannula.codegen.base import (
    ast_for_annotation_assignment,
    ast_for_assign,
    ast_for_class_field,
    ast_for_constant,
    ast_for_docstring,
    ast_for_function_body,
    ast_for_import_from,
    ast_for_keyword,
    ast_for_name,
    ast_for_single_subscript,
    ast_for_union_subscript,
)
from cannula.types import Field, UnionType
from cannula.codegen.schema_analyzer import CodeGenerator, TypeInfo

LOG = logging.getLogger(__name__)


T = TypeVar("T")


class PythonCodeGenerator(CodeGenerator):
    """Generates Python code from analyzed GraphQL schema"""

    use_pydantic: bool

    def render_computed_field(self, field: Field) -> ast.AsyncFunctionDef:
        """Create an AST node for a computed field method"""
        args = [
            ast.arg("self"),
            ast.arg(
                "info",
                annotation=ast_for_single_subscript(
                    ast_for_name("ResolveInfo"), ast_for_constant("Context")
                ),
            ),
            *field.positional_args,
        ]

        args_node = ast.arguments(
            args=args,
            vararg=None,
            posonlyargs=[],
            kwonlyargs=field.kwonlyargs,
            kw_defaults=field.kwdefaults,
            kwarg=None,
            defaults=[],
        )

        return ast.AsyncFunctionDef(
            name=field.name,
            args=args_node,
            body=ast_for_function_body(field),
            decorator_list=[ast.Name(id="abstractmethod", ctx=ast.Load())],
            returns=ast.Name(id=field.type, ctx=ast.Load()),
            type_params=[],
        )

    def render_interface_type(
        self, type_info: TypeInfo[GraphQLInterfaceType]
    ) -> list[ast.stmt]:
        """Create AST nodes for an interface type"""
        # Create class body
        body: list[ast.stmt] = []
        if type_info.description:
            body.append(ast_for_docstring(type_info.description))

        # Add fields as stmts
        for field in type_info.fields:
            body.append(ast_for_class_field(field))

        return [
            cast(
                ast.stmt,
                ast.ClassDef(
                    name=type_info.py_type,
                    bases=[ast_for_name("Protocol")],
                    keywords=[],
                    body=body,
                    decorator_list=[],
                    type_params=[],
                ),
            )
        ]

    def render_object_type(
        self,
        type_info: TypeInfo[GraphQLObjectType],
        use_pydantic: bool,
    ) -> list[ast.stmt]:
        """Create AST nodes for an object type"""
        # Create class body
        body: list[ast.stmt] = []
        if type_info.description:
            body.append(ast_for_docstring(type_info.description))

        # Add type definition as stmt
        type_def = ast_for_assign("__typename", ast_for_constant(type_info.name))
        body.append(type_def)

        # Render non-computed as class vars and add them to body first
        normal_fields: list[ast.stmt] = [
            ast_for_class_field(f) for f in type_info.fields if not f.is_computed
        ]
        body.extend(normal_fields)

        # Render computed fields as functions and add them at end of body
        computed_fields: list[ast.stmt] = [
            self.render_computed_field(f) for f in type_info.fields if f.is_computed
        ]
        body.extend(computed_fields)

        base_class = "BaseModel" if use_pydantic else "ABC"
        decorators: list[ast.expr] = []
        if not use_pydantic:
            decorators.append(
                ast.Call(
                    func=ast_for_name("dataclass"),
                    args=[],
                    keywords=[ast_for_keyword("kw_only", True)],
                )
            )

        return [
            cast(
                ast.stmt,
                ast.ClassDef(
                    name=type_info.py_type,
                    bases=[ast_for_name(base_class)],
                    keywords=[],
                    body=body,
                    decorator_list=decorators,
                    type_params=[],
                ),
            )
        ]

    def render_union_type(self, type_info: UnionType) -> list[ast.stmt]:
        """Create AST nodes for a union type"""
        member_types = [t.safe_value for t in type_info.types]
        return [
            cast(
                ast.stmt,
                ast_for_assign(
                    type_info.name,
                    ast_for_union_subscript(*member_types),
                ),
            )
        ]

    def render_input_type(
        self, type_info: TypeInfo[GraphQLInputObjectType]
    ) -> list[ast.stmt]:
        """Create AST nodes for an input type"""
        body: list[ast.stmt] = [
            cast(
                ast.stmt,
                ast_for_annotation_assignment(
                    f.name,
                    # For input types we need to include all fields as required
                    # since the resolver will fill in the default values if not provided
                    annotation=ast_for_name(f.field_type.safe_value),
                ),
            )
            for f in type_info.fields
        ]

        return [
            cast(
                ast.stmt,
                ast.ClassDef(
                    name=type_info.py_type,
                    bases=[ast_for_name("TypedDict")],
                    keywords=[],
                    body=body,
                    decorator_list=[],
                    type_params=[],
                ),
            )
        ]

    def ast_for_operation(self, field: Field) -> ast.ClassDef:
        func = self.render_operation_field_ast(field)
        return ast.ClassDef(
            name=field.func_name,
            body=[func],
            bases=[ast_for_name("Protocol")],
            keywords=[],
            decorator_list=[],
            type_params=[],
        )

    def render_operation_field_ast(self, field: Field) -> ast.AsyncFunctionDef:
        """
        Render a computed field as an AST node for a function definition.
        """
        args = [
            ast.arg("self"),
            ast.arg(
                "info",
                annotation=ast_for_single_subscript(
                    ast_for_name("ResolveInfo"), ast_for_constant("Context")
                ),
            ),
            *field.positional_args,
        ]
        args_node = ast.arguments(
            args=args,
            vararg=None,
            posonlyargs=[],
            kwonlyargs=field.kwonlyargs,
            kw_defaults=field.kwdefaults,
            kwarg=None,
            defaults=[],
        )
        func_node = ast.AsyncFunctionDef(
            name="__call__",
            args=args_node,
            body=ast_for_function_body(field),
            decorator_list=[],
            returns=ast.Name(id=field.type, ctx=ast.Load()),
            type_params=[],
        )
        return func_node

    def render_operation_types(self) -> list[ast.stmt]:
        """Create AST nodes for operation (Query/Mutation) types"""
        operation_fields: List[Field] = []
        field_classes: list[ast.stmt] = []

        for field in self.analyzer.operation_fields:
            if field.name == "_empty":
                continue

            operation_fields.append(field)
            field_classes.append(cast(ast.stmt, self.ast_for_operation(field)))

        if field_classes:
            root_type = ast.ClassDef(
                name="RootType",
                body=cast(
                    list[ast.stmt],
                    [
                        ast_for_annotation_assignment(
                            f.name, annotation=ast_for_name(f.operation_type)
                        )
                        for f in operation_fields
                    ],
                ),
                bases=[ast_for_name("TypedDict")],
                keywords=[ast_for_keyword("total", False)],
                decorator_list=[],
                type_params=[],
            )
            field_classes.append(cast(ast.stmt, root_type))

        return field_classes

    def render_type_checking(self):
        return ast.If(
            test=ast_for_name("TYPE_CHECKING"),
            body=[
                ast_for_import_from(
                    module="context",
                    names={"Context"},
                    level=1,
                )
            ],
            orelse=[],
        )

    def generate(self, use_pydantic: bool) -> str:
        """Generate complete Python code from the schema"""
        body: list[ast.stmt] = [self.render_type_checking()]

        # Generate code for each type
        for interface in self.analyzer.interface_types:
            body.extend(cast(list[ast.stmt], self.render_interface_type(interface)))

        for input_type in self.analyzer.input_types:
            body.extend(cast(list[ast.stmt], self.render_input_type(input_type)))

        for obj_type in self.analyzer.object_types:
            obj = self.render_object_type(obj_type, use_pydantic)
            body.extend(cast(list[ast.stmt], obj))

        for union_type in self.analyzer.union_types:
            body.extend(cast(list[ast.stmt], self.render_union_type(union_type)))

        # Generate operation types
        body.extend(cast(list[ast.stmt], self.render_operation_types()))

        module = self.create_module(body)
        return format_code(module)
