import ast
import re
import typing

from graphql import parse, DocumentNode

# AST contants for common values
NONE = ast.Constant(value=None)
ELLIPSIS = ast.Expr(value=ast.Constant(value=Ellipsis))
PASS = ast.Pass()


def gql(schema: str) -> DocumentNode:
    """
    Helper utility to provide help mark up
    """
    return parse(schema)


def parse_metadata_to_yaml(description: str) -> str:
    """
    Parse GraphQL description with @metadata directive into description with YAML metadata.

    Args:
        description: GraphQL description string with optional @metadata directive

    Returns:
        String with description and parsed metadata in YAML format
    """
    metadata_match = re.search(r"@metadata\((.*)\)$", description)

    if not metadata_match:
        return description

    metadata_str = metadata_match.group(1)
    clean_desc = description[: metadata_match.start()].strip()

    # Parse the metadata string into proper key-value pairs
    metadata_dict = parse_metadata_pairs(metadata_str)

    # Convert to YAML format
    yaml_lines = ["metadata:"]
    for key, value in metadata_dict.items():
        # Properly format the value based on type
        if isinstance(value, bool):
            formatted_value = str(value).lower()
        elif isinstance(value, (int, float)):
            formatted_value = str(value)
        else:
            # Quote string values that might cause YAML issues
            formatted_value = f'"{value}"' if need_quotes(value) else value

        yaml_lines.append(f"  {key}: {formatted_value}")

    return f"{clean_desc}\n---\n" + "\n".join(yaml_lines)


def parse_metadata_pairs(metadata_str: str) -> dict:
    """
    Parse metadata string into dictionary of key-value pairs.
    Handles cases like 'foo:bar' and 'foo: bar'.
    """
    pairs = {}
    # Split on commas that aren't inside quotes
    for pair in re.findall(r'(?:[^,"]|"(?:\\.|[^"])*")+', metadata_str):
        pair = pair.strip()
        if not pair:  # pragma: no cover
            continue

        # Handle key-value separation with or without spaces
        match = re.match(r"(\w+)\s*:\s*(.+)", pair)
        if match:
            key, value = match.groups()
            # Convert value to appropriate type
            pairs[key] = parse_value(value.strip())

    return pairs


def parse_value(value: str) -> typing.Union[str, bool, int, float]:
    """Parse string value into appropriate type."""
    value = value.strip('"')

    # Handle booleans
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False

    # Handle numbers
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def need_quotes(value: str) -> bool:
    """Check if a string value needs to be quoted in YAML."""
    # Add characters or patterns that would make YAML invalid
    special_chars = ":,[]{}#&*!|>'\"%@`/ "
    return any(c in value for c in special_chars) or value.strip() != value


def ast_for_import_from(module: str, names: set[str], level: int = 0) -> ast.ImportFrom:
    ast_names = []
    _names = list(names)
    _names.sort()
    for name in _names:
        ast_name = ast.alias(name=name, asname=None)
        ast_names.append(ast_name)
    return ast.ImportFrom(module=module, names=ast_names, level=level)


def ast_for_name(name: str) -> ast.expr:
    return ast.Name(id=name, ctx=ast.Load())


def ast_for_constant(value: typing.Any) -> ast.expr:
    return ast.Constant(value=value)


def ast_for_docstring(value: str) -> ast.Expr:
    return ast.Expr(value=ast_for_constant(value))


def ast_for_annotation_assignment(
    target: str, annotation: ast.expr, default: typing.Optional[typing.Any] = None
) -> ast.AnnAssign:
    return ast.AnnAssign(
        target=ast.Name(id=target, ctx=ast.Store()),
        annotation=annotation,
        value=default,
        simple=1,
    )


def ast_for_assign(target: str, value: ast.expr) -> ast.Assign:
    targets = [ast_for_name(target)]
    return ast.Assign(
        targets=targets,
        value=value,
        lineno=None,  # type: ignore
    )


def ast_for_keyword(arg: str, value: typing.Any) -> ast.keyword:
    return ast.keyword(arg=arg, value=ast_for_constant(value))


def ast_for_subscript(
    value: typing.Union[ast.Name, ast.Attribute, ast.expr], *items: str
) -> ast.Subscript:
    use_tuple = len(items) > 1
    item_names = [ast_for_name(item) for item in items]
    _slice = ast.Tuple(elts=item_names, ctx=ast.Load()) if use_tuple else item_names[0]
    return ast.Subscript(value=value, slice=_slice, ctx=ast.Load())


def ast_for_single_subscript(
    value: typing.Union[ast.Name, ast.Attribute, ast.expr], item: ast.expr
) -> ast.Subscript:
    return ast.Subscript(value=value, slice=item, ctx=ast.Load())


def ast_for_union_subscript(*items: str) -> ast.Subscript:
    value = ast_for_name("Union")
    return ast_for_subscript(value, *items)
