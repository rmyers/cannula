from contextlib import asynccontextmanager

from fastapi import FastAPI, Request


from dashboard.core.config import config
from dashboard.core.database import create_tables
from dashboard.core.session import SessionMiddleware, auth_router
from dashboard.part1.routes import part1
from dashboard.part2.routes import part2


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Make sure the database has been created
    await create_tables()
    # Run the app
    yield
    # tear down things right now there is nothing to do


app = FastAPI(
    debug=config.debug,
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware)


@app.get("/")
def home(request: Request):
    return config.templates.TemplateResponse(request, "index.html")


app.include_router(auth_router)
app.include_router(part1)
app.include_router(part2)
