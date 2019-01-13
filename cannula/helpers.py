import os
import pkgutil
import sys


def get_root_path(import_name):
    """Returns the path to a package or cwd if that cannot be found.

    Inspired by [flask](https://github.com/pallets/flask/blob/master/flask/helpers.py)
    """
    # Module already imported and has a file attribute. Use that first.
    mod = sys.modules.get(import_name)
    if mod is not None and hasattr(mod, '__file__'):
        return os.path.dirname(os.path.abspath(mod.__file__))

    # Next attempt: check the loader.
    loader = pkgutil.get_loader(import_name)

    # Loader does not exist or we're referring to an unloaded main module
    # or a main module without path (interactive sessions), go with the
    # current working directory.
    if loader is None or import_name == '__main__':
        return os.getcwd()

    filepath = loader.get_filename(import_name)
    return os.path.dirname(os.path.abspath(filepath))
