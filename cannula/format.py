import ast
import os
import pathlib
import subprocess
import tempfile

RUFF_CMD = os.getenv("RUFF_CMD", "ruff")


def format_with_ruff(root: ast.Module, dest: pathlib.Path):
    # Convert AST to source code
    source_code = ast.unparse(root)

    # Write the unformatted source code to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".py") as tmp:
        tmp_path = pathlib.Path(tmp.name)
        tmp.write(source_code)

    # Format the temporary file using ruff
    subprocess.run([RUFF_CMD, "check", "--fix-only", tmp_path], check=True)
    subprocess.run([RUFF_CMD, "format", tmp_path], check=True)

    # Read back the formatted code
    with open(tmp_path, "r") as tmp:
        formatted_code = tmp.read()

    # Write the formatted code to the desired file
    with open(dest, "w") as final_file:
        final_file.write(formatted_code)

    # Clean up the temporary file
    tmp_path.unlink()
