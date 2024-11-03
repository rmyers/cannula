from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .core.config import config
from .core.database import create_tables
from .core.session import SessionMiddleware, auth_router
from .part1.routes import part1
from .part2.routes import part2
from .part3.routes import part3
from .part4.routes import part4


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
origins = [
    "http://localhost",
    "http://localhost:8000",
    "https://studio.apollographql.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware)


@app.get("/")
def home(request: Request):
    return config.templates.TemplateResponse(request, "index.html")


app.include_router(auth_router)
app.include_router(part1)
app.include_router(part2)
app.include_router(part3)
app.include_router(part4)
