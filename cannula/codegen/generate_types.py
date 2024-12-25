import ast
import collections
import logging
from typing import Iterable, Tuple, Union, List
from graphql import (
    DocumentNode,
    GraphQLObjectType,
)

from cannula.scalars import ScalarInterface
from cannula.schema import Imports, build_and_extend_schema

from cannula.format import format_code
from cannula.codegen.base import (
    ast_for_annotation_assignment,
    ast_for_argument,
    ast_for_assign,
    ast_for_docstring,
    ast_for_constant,
    ast_for_function_body,
    ast_for_import_from,
    ast_for_name,
    ast_for_union_subscript,
    fix_missing_locations,
)
from cannula.types import Argument, Field
from cannula.codegen.schema_analyzer import SchemaAnalyzer, TypeInfo

LOG = logging.getLogger(__name__)

_IMPORTS: Imports = collections.defaultdict(set[str])
_IMPORTS.update(
    {
        "__future__": {"annotations"},
        "abc": {"ABC", "abstractmethod"},
        "cannula": {"ResolveInfo"},
        "dataclasses": {"dataclass"},
        "pydantic": {"BaseModel"},
        "typing": {
            "Any",
            "Awaitable",
            "Sequence",
            "Optional",
            "Protocol",
            # In python < 3.12 pydantic wants us to use typing_extensions
            # "TypedDict",
            "Union",
        },
        "typing_extensions": {"TypedDict", "NotRequired"},
        "sqlalchemy": {"ForeignKey", "select", "func"},
        "sqlalchemy.ext.asyncio": {"AsyncAttrs"},
        "sqlalchemy.orm": {
            "DeclarativeBase",
            "mapped_column",
            "Mapped",
            "relationship",
        },
    }
)


class PythonCodeGenerator:
    """Generates Python code from analyzed GraphQL schema"""

    def __init__(self, analyzer: SchemaAnalyzer, use_pydantic: bool = False):
        self.analyzer = analyzer
        self.use_pydantic = use_pydantic

    def render_function_args_ast(
        self,
        args: list[Argument],
    ) -> Tuple[list[ast.arg], list[ast.arg], list[ast.expr | None]]:
        """
        Render function arguments as AST nodes.

        This returns a tuple of lists (args, kwargs, defaults). If the field is required
        it is added to args, if it is not required then it is added to kwargs along
        with a default in the defaults list.
        """
        pos_args_ast: list[ast.arg] = [
            ast_for_argument(arg) for arg in args if arg.required
        ]
        kwonly_args_ast: list[ast.arg] = [
            ast_for_argument(arg) for arg in args if not arg.required
        ]
        defaults: list[ast.expr | None] = [
            ast_for_constant(arg.default) for arg in args if not arg.required
        ]
        return pos_args_ast, kwonly_args_ast, defaults

    def render_computed_field(
        self, field: Field, parent_type: str
    ) -> ast.AsyncFunctionDef:
        """Create an AST node for a computed field method"""
        pos_args, kwonlyargs, defaults = self.render_function_args_ast(field.args)
        args = [
            ast.arg("self"),
            ast.arg("info", annotation=ast_for_name("ResolveInfo")),
            *pos_args,
        ]

        # Create function arguments node
        args_node = ast.arguments(
            args=args,
            vararg=None,
            posonlyargs=[],
            kwonlyargs=kwonlyargs,
            kw_defaults=defaults,
            kwarg=None,
            defaults=[],
        )

        # Create function body
        body = []
        if field.description:
            body.append(ast_for_docstring(field.description))
        body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))

        return ast.AsyncFunctionDef(
            name=field.name,
            args=args_node,
            body=body,
            decorator_list=[ast.Name(id="abstractmethod", ctx=ast.Load())],
            returns=ast.Name(id=field.type, ctx=ast.Load()),
        )

    def render_class_field(self, field: Field) -> ast.AnnAssign:
        """Create an AST node for a class field"""
        field_type = ast_for_name(field.type)
        default = ast_for_constant(None) if not field.required else None

        return ast_for_annotation_assignment(
            field.name, annotation=field_type, default=default
        )

    def render_object_type(
        self, type_info: TypeInfo[GraphQLObjectType]
    ) -> List[ast.AST]:
        """Create AST nodes for an object type"""
        # Separate computed and non-computed fields

        computed_fields = [f for f in type_info.fields if f.is_computed]
        normal_fields = [f for f in type_info.fields if not f.is_computed]

        # Create type definition constant
        type_def = ast_for_assign("__typename", ast_for_constant(type_info.name))

        # Create class body
        body = []
        if type_info.description:
            body.append(ast_for_docstring(type_info.description))
        body.append(type_def)

        # Add fields
        body.extend(self.render_class_field(f) for f in normal_fields)
        body.extend(
            self.render_computed_field(f, type_info.name) for f in computed_fields
        )

        # Create class definition
        base_class = "BaseModel" if self.use_pydantic else "ABC"
        decorators = []
        if not self.use_pydantic:
            decorators.append(
                ast.Call(
                    func=ast_for_name("dataclass"),
                    args=[],
                    keywords=[
                        ast.keyword(arg="kw_only", value=ast.Constant(value=True))
                    ],
                )
            )

        return [
            ast.ClassDef(
                name=type_info.py_type,
                bases=[ast_for_name(base_class)],
                keywords=[],
                body=body,
                decorator_list=decorators,
            )
        ]

    def render_union_type(self, type_info) -> List[ast.AST]:
        """Create AST nodes for a union type"""
        member_types = [t.name for t in type_info.type_def.types]
        return [
            ast_for_assign(
                type_info.name,
                ast_for_union_subscript(*member_types),
            )
        ]

    def render_input_type(self, type_info: TypeInfo) -> List[ast.ClassDef]:
        """Create AST nodes for an input type"""
        body = [
            ast_for_annotation_assignment(f.name, annotation=ast_for_name(f.type))
            for f in type_info.fields
        ]

        return [
            ast.ClassDef(
                name=type_info.py_type,
                bases=[ast_for_name("TypedDict")],
                keywords=[],
                body=[*body],
                decorator_list=[],
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
            # type_params=[],
        )

    def render_operation_field_ast(self, field: Field) -> ast.AsyncFunctionDef:
        """
        Render a computed field as an AST node for a function definition.
        """
        pos_args, kwonlyargs, defaults = self.render_function_args_ast(field.args)
        args = [
            ast.arg("self"),
            ast.arg("info", annotation=ast_for_name("ResolveInfo")),
            *pos_args,
        ]
        # value = field.value if field.required else f"Optional[{field.value}]"
        args_node = ast.arguments(
            args=args,
            vararg=None,
            posonlyargs=[],
            kwonlyargs=kwonlyargs,
            kw_defaults=defaults,
            kwarg=None,
            defaults=[],
        )
        func_node = ast.AsyncFunctionDef(
            name="__call__",
            args=args_node,
            body=ast_for_function_body(field),
            decorator_list=[],
            returns=ast.Name(id=field.type, ctx=ast.Load()),
        )
        return func_node

    def render_operation_types(self) -> List[ast.AST]:
        """Create AST nodes for operation (Query/Mutation) types"""
        operation_fields: List[Field] = []
        field_classes = []

        for field in self.analyzer.operation_fields:
            if field.name == "_empty":
                continue

            operation_fields.append(field)
            # Create operation class
            field_classes.append(self.ast_for_operation(field))

        # Create root type if we have operations
        if field_classes:
            root_type = ast.ClassDef(
                name="RootType",
                body=[
                    ast_for_annotation_assignment(
                        f.name, annotation=ast_for_name(f.operation_type)
                    )
                    for f in operation_fields
                ],
                bases=[ast_for_name("TypedDict")],
                keywords=[ast.keyword(arg="total", value=ast_for_constant(False))],
                decorator_list=[],
            )
            field_classes.append(root_type)

        return field_classes

    def generate(self) -> str:
        """Generate complete Python code from the schema"""
        module = ast.Module(body=[], type_ignores=[])

        # Add imports
        for module_name, names in self.analyzer.extensions.imports.items():
            if module_name == "builtins":
                continue
            module.body.append(ast_for_import_from(module=module_name, names=names))

        # Generate code for each type
        for type_info in self.analyzer.interface_types.values():
            module.body.extend(self.render_object_type(type_info))  # type: ignore

        for type_info in self.analyzer.input_types.values():
            module.body.extend(self.render_input_type(type_info))  # type: ignore

        for type_info in self.analyzer.object_types.values():
            module.body.extend(self.render_object_type(type_info))  # type: ignore

        for type_info in self.analyzer.union_types:
            module.body.extend(self.render_union_type(type_info))  # type: ignore

        # Generate operation types
        module.body.extend(self.render_operation_types())  # type: ignore

        module = fix_missing_locations(module)
        # return ast.unparse(module)
        return format_code(module)


def render_code(
    type_defs: Iterable[Union[str, DocumentNode]],
    scalars: List[ScalarInterface] = [],
    use_pydantic: bool = False,
) -> str:
    """Generate Python code from GraphQL schema"""
    schema = build_and_extend_schema(type_defs, scalars, {"imports": _IMPORTS})
    analyzer = SchemaAnalyzer(schema)
    generator = PythonCodeGenerator(analyzer, use_pydantic)
    return generator.generate()
