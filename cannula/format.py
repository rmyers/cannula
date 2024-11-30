import ast
import logging

import autoflake
import black

# Disable noisy debug logs
black_log = logging.getLogger("blib2to3")
black_log.setLevel(logging.ERROR)


def format_code(root: ast.Module):
    # Convert AST to source code
    source_code = ast.unparse(root)

    # Remove unused imports and variables
    fixed_code = autoflake.fix_code(
        source=source_code,
        remove_all_unused_imports=True,
        remove_unused_variables=True,
        remove_duplicate_keys=True,
    )

    # format with black
    formatted_code = black.format_str(fixed_code, mode=black.FileMode())

    return formatted_code
