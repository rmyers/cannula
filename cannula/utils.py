import re
import typing

from graphql import parse, DocumentNode


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
    special_chars = ":,[]{}#&*!|>'\"%@`"
    return any(c in value for c in special_chars) or value.strip() != value
