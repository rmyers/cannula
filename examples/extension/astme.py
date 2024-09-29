#!/usr/bin/env python
import ast


def main():
    with open("_generated.py") as f:
        tree = ast.parse(f.read())
    print(ast.dump(tree, indent=4))


if __name__ == "__main__":
    main()
