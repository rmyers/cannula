import ast
import logging
from typing import List, cast

from cannula.format import format_code
from cannula.utils import (
    ELLIPSIS,
    ast_for_annotation_assignment,
    ast_for_assign,
    ast_for_constant,
    ast_for_docstring,
    ast_for_import_from,
    ast_for_keyword,
    ast_for_name,
    ast_for_single_subscript,
)
from cannula.types import Field
from cannula.codegen.schema_analyzer import CodeGenerator, ObjectType

LOG = logging.getLogger(__name__)


def ast_for_function_body(field: Field) -> list[ast.stmt]:
    body: list[ast.stmt] = []
    if field.description:
        body.append(ast_for_docstring(field.description))

    body.append(ELLIPSIS)
    return body


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

    def render_object_type(
        self,
        type_info: ObjectType,
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
            f.as_class_var for f in type_info.fields if not f.is_computed
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

    def ast_for_operation(self, field: Field) -> ast.ClassDef:
        func = self.render_operation_field_ast(field)
        return ast.ClassDef(
            name=field.operation_name,
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
            body.append(interface.as_ast)

        for input_type in self.analyzer.input_types:
            body.append(input_type.as_ast)

        for obj_type in self.analyzer.object_types:
            obj = self.render_object_type(obj_type, use_pydantic)
            body.extend(cast(list[ast.stmt], obj))

        for union_type in self.analyzer.union_types:
            body.append(union_type.as_ast)

        # Generate operation types
        body.extend(cast(list[ast.stmt], self.render_operation_types()))

        module = self.create_module(body)
        return format_code(module)
