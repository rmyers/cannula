import pathlib

import fastapi
from fastapi.templating import Jinja2Templates

root = pathlib.Path(__file__).parent

templates = Jinja2Templates(root / "templates")
app = fastapi.FastAPI(debug=True)


@app.get("/")
def home(request: fastapi.Request):
    return templates.TemplateResponse(request, "index.html")
