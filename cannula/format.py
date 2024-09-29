import ast
import subprocess
import tempfile
import pathlib


def format_with_ruff(root: ast.Module, dest: pathlib.Path):

    # # Assuming `root` is your AST root node
    # root = ast.Module(body=[], type_ignores=[])
    # # Example of adding a simple function to the AST
    # root.body.append(
    #     ast.FunctionDef(
    #         name="hello_world",
    #         args=ast.arguments(
    #             posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
    #         ),
    #         body=[ast.Expr(value=ast.Constant(value="Hello, world!"))],
    #         decorator_list=[],
    #     )
    # )

    # Convert AST to source code
    source_code = ast.unparse(root)

    # Write the unformatted source code to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".py") as tmp:
        tmp_path = pathlib.Path(tmp.name)
        tmp.write(source_code)

    # Format the temporary file using ruff
    subprocess.run(["ruff", "check", "--fix-only", tmp_path], check=True)
    subprocess.run(["ruff", "format", tmp_path], check=True)

    # Read back the formatted code
    with open(tmp_path, "r") as tmp:
        formatted_code = tmp.read()

    # Write the formatted code to the desired file
    with open(dest, "w") as final_file:
        final_file.write(formatted_code)

    # Clean up the temporary file
    tmp_path.unlink()
