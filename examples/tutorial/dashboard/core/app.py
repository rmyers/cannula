from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from dashboard.core.config import config
from dashboard.core.database import create_tables


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


@app.get("/")
def home(request: Request):
    return config.templates.TemplateResponse(request, "index.html")
