from jinja2 import BaseLoader, TemplateNotFound, Environment
from pathlib import Path
from typing import Callable, Optional, Union
from contextvars import ContextVar


# Context variable to track current template path
current_template: ContextVar[Optional[str]] = ContextVar(
    "current_template", default=None
)


class NextJSStyleLoader(BaseLoader):
    def __init__(self, root_path: Union[str, Path]):
        """
        Initialize the loader with a root path for templates.

        Args:
            root_path: The root directory containing all templates
        """
        self.root_path = Path(root_path).resolve()

    def get_source(
        self, environment: "Environment", template: str
    ) -> tuple[str, str, Optional[Callable]]:
        """
        Get the template source, filename, and uptodate callable.

        Args:
            environment: Jinja environment
            template: Template name/path

        Returns:
            Tuple of (source code, filename, uptodate callable)

        Raises:
            TemplateNotFound: If template cannot be found
        """
        template_path = Path(template)

        # If it's an absolute path (starts with /), search from root
        if template.startswith("/"):
            search_path = self.root_path / template_path.relative_to("/")
            if search_path.exists():
                return self._read_template_and_set_current(search_path)
            raise TemplateNotFound(template)

        # For relative paths (./file.html or ../file.html), use current template path
        if template.startswith("./") or template.startswith("../"):
            current = current_template.get()
            if current is None:
                raise TemplateNotFound(
                    f"Cannot resolve relative path {template} without current template context"
                )
            search_path = (Path(current).parent / template_path).resolve()
            if self.root_path in search_path.parents and search_path.exists():
                return self._read_template_and_set_current(search_path)
            raise TemplateNotFound(template)

        # For extends statements and non-absolute imports, search up from current directory
        current = current_template.get()
        if current is not None:
            # Start searching from the current template's directory
            current_dir = Path(current).parent
            while True:
                test_path = current_dir / template_path
                if test_path.exists():
                    source = self._read_template_and_set_current(test_path)
                    return source

                # Stop if we've reached the root
                if len(current_dir.parts) <= len(self.root_path.parts):
                    break

                current_dir = current_dir.parent

        # If not found or no current context, try from root
        root_path = self.root_path / template_path
        if root_path.exists():
            return self._read_template_and_set_current(root_path)

        raise TemplateNotFound(template)

    def _read_template_and_set_current(
        self, path: Path
    ) -> tuple[str, str, Optional[Callable]]:
        """
        Read a template and set it as the current template in context var.

        Args:
            path: Path to the template file

        Returns:
            Tuple of (source code, filename, uptodate callable)
        """
        source, filename, uptodate = self._read_template(path)
        current_template.set(filename)
        return source, filename, uptodate

    def _read_template(self, path: Path) -> tuple[str, str, Optional[Callable]]:
        """
        Read a template file and return the source tuple.

        Args:
            path: Path to the template file

        Returns:
            Tuple of (source code, filename, uptodate callable)
        """
        path = path.resolve()
        with open(path, "r") as f:
            source = f.read()

        # Return source and filename, with an uptodate callable
        # last_mtime = path.stat().st_mtime

        def uptodate() -> bool:
            return False

        self._last_mtime = path.stat().st_mtime
        return source, str(path), uptodate
