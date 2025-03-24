import contextlib
import logging
import pathlib
import typing

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import BaseRoute, Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from cannula.api import CannulaAPI, RootType
from cannula.context import Context, Settings
from cannula.handlers.asgi import GraphQLHandler
from cannula.handlers.operations import HTMXHandler
from cannula.utils import get_config, resolve_scalars

logger = logging.getLogger(__name__)


class AppState(typing.TypedDict):
    http_client: httpx.AsyncClient


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> typing.AsyncIterator[AppState]:
    logger.debug("Setting up http_client")
    async with httpx.AsyncClient() as client:
        yield {"http_client": client}


class AppRouter:
    def __init__(
        self,
        templates_dir: pathlib.Path,
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


class CannulaApplication(typing.Generic[RootType, Settings], Starlette):

    def __init__(
        self,
        *,
        start_path: typing.Optional[pathlib.Path] = None,
        context: typing.Optional[type[Context[Settings]]] = None,
        config: typing.Optional[Settings] = None,
        root_value: typing.Optional[RootType] = None,
        debug: bool = False,
        **kwargs,
    ):
        _py_config = get_config(start_path)

        self.api = CannulaAPI[RootType, Settings](
            schema=_py_config.schema,
            context=context,
            config=config,
            root_value=root_value,
            scalars=resolve_scalars(_py_config.scalars),
            operations=_py_config.operations,
            debug=debug,
        )

        # Setup the routes for this application starting with the static directory
        routes: typing.List[BaseRoute] = [
            Mount(
                "/static",
                app=StaticFiles(
                    directory=_py_config.static_directory,
                    check_dir=False,
                    packages=["cannula"],
                ),
                name="static",
            )
        ]

        # TODO(rmyers): add options here
        graphql_handler = GraphQLHandler(self.api)
        routes.extend(graphql_handler.routes())

        application = AppRouter(_py_config.app_directory)
        routes.extend(application.discover_routes())

        if self.api.operations is not None:
            handler = HTMXHandler(self.api, _py_config.operations_directory)
            routes.append(Route("/operation/{name:str}", handler.handle_request))
            routes.append(
                Route(
                    "/operation/{name:str}", handler.handle_mutation, methods=["POST"]
                )
            )

        super().__init__(routes=routes, debug=debug, lifespan=lifespan, **kwargs)
