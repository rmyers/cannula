from starlette.requests import Request
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from pathlib import Path
import typing

import logging

logger = logging.getLogger(__name__)


class AppRouter:
    def __init__(
        self,
        templates_dir: Path,
        debug: bool = False,
    ):
        self.templates_dir = templates_dir
        self.debug = debug

        logger.debug(f"Initializing AppRouter with: {self.templates_dir}")

        self.templates = Jinja2Templates(directory=self.templates_dir)

    def discover_routes(self) -> typing.List[Route]:
        """Automatically discover and create routes based on template directory structure."""
        logger.debug("Starting route discovery...")

        routes = []

        for template_path in self.templates_dir.rglob("page.html"):
            logger.debug(f"\nProcessing template: {template_path}")
            relative_path = template_path.relative_to(self.templates_dir)
            parent_dir = relative_path.parent

            resolved_template_path = str(relative_path)

            # Skip over hidden folders
            if resolved_template_path.startswith("_"):
                continue

            # Convert template path to URL path
            if parent_dir.name == "":
                url_path = "/"
            else:
                url_path = f"/{parent_dir}"

            # Handle dynamic routes (e.g., [id]/page.html becomes /{id})
            url_path = str(url_path).replace("[", "{").replace("]", "}")

            # Create route handler
            async def get_handler(request: Request, template=str(relative_path)):
                # Extract dynamic parameters from request path
                template_context = request.path_params
                return self.templates.TemplateResponse(
                    request,
                    template,
                    context=template_context,
                )

            routes.append(Route(url_path, get_handler, methods=["GET"]))

        return routes
