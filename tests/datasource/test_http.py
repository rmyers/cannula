import typing
import httpx
import fastapi
import pydantic

from cannula.datasource import http
import pytest


class Widgety(pydantic.BaseModel):
    some: str


WIDGETS: list[Widgety] = [Widgety(some="thing")]


class MockDB:
    # This is just a object that we can use in assertions
    # that it was called the specific number of times
    def get_widgets(self) -> list[Widgety]:
        return WIDGETS

    def add_widget(self, data: Widgety) -> Widgety:
        data.model_fields
        WIDGETS.append(data)
        return data

    def delete_all(self) -> None:
        global WIDGETS
        WIDGETS = []


class Widget(http.HTTPDatasource, source=http.SourceHTTP(baseURL="http://localhost")):

    async def did_receive_response(
        self, response: httpx.Response, request: httpx.Request
    ) -> http.Response:
        print(response.text)
        return await super().did_receive_response(response, request)

    async def get_widgets(self) -> list[Widgety]:
        response = await self.get("widgets")
        return await self.get_models(Widgety, response)

    async def post_widget(self, data: Widgety) -> Widgety:
        response = await self.post("/widgets", json=data.model_dump())
        return await self.get_model(Widgety, response)

    async def put_widget(self, data: Widgety) -> Widgety:
        response = await self.put("/widgets", json=data.model_dump())
        return await self.get_model(Widgety, response)

    async def patch_widget(self, data: Widgety) -> Widgety:
        response = await self.patch("/widgets", json=data.model_dump())
        return await self.get_model(Widgety, response)

    async def delete_widget(self) -> None:
        await self.delete("/widgets")
        return None

    async def head_widgets(self) -> int:
        response = await self.head("widgets")
        response = typing.cast(httpx.Response, response)
        return response.headers.get("Content-length")

    async def options_widgets(self) -> typing.Any:
        return await self.options("widgets")

    async def get_model_from_response_invalid(self) -> Widgety:
        # Should raise Attribute error
        return await self.get_model(Widgety, [{"some": "thing"}])

    async def get_model_list_from_response_invalid(self) -> list[Widgety]:
        # Should raise Attribute error
        return await self.get_models(Widgety, {"some": "thing"})


mockDB = MockDB()
fake_app = fastapi.FastAPI()


@fake_app.get("/widgets")
async def get_widgets():
    return mockDB.get_widgets()


@fake_app.head("/widgets")
async def head_widgets():
    results = mockDB.get_widgets()
    response = fastapi.Response(headers={"Content-length": str(len(results))})
    return response


@fake_app.options("/widgets")
async def options_widgets():
    mockDB.get_widgets()
    return ["GET", "HEAD", "POST", "OPTIONS"]


@fake_app.post("/widgets")
async def post_widgets(widget: Widgety):
    return mockDB.add_widget(widget)


@fake_app.put("/widgets")
async def put_widgets(widget: Widgety):
    return mockDB.add_widget(widget)


@fake_app.patch("/widgets")
async def patch_widgets(widget: Widgety):
    return mockDB.add_widget(widget)


@fake_app.delete("/widgets")
async def delete_widgets():
    return mockDB.delete_all()


@pytest.fixture
def mocked_client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=fake_app))


@pytest.fixture
def widget(mocked_client) -> Widget:
    return Widget(client=mocked_client)


async def test_http_datasource_caches_get(mocker, widget: Widget):
    get_widget_spy = mocker.spy(mockDB, "get_widgets")

    results_one = await widget.get_widgets()
    results_two = await widget.get_widgets()

    assert results_one == results_two
    assert isinstance(results_one, list)
    assert results_one[0].some == "thing"

    get_widget_spy.assert_called_once_with()


async def test_http_datasource_caches_head(mocker, widget: Widget):
    get_widget_spy = mocker.spy(mockDB, "get_widgets")

    results_one = await widget.head_widgets()
    results_two = await widget.head_widgets()

    assert results_one == results_two

    get_widget_spy.assert_called_once_with()


async def test_http_datasource_caches_options(mocker, widget: Widget):
    get_widget_spy = mocker.spy(mockDB, "get_widgets")

    results_one = await widget.options_widgets()
    results_two = await widget.options_widgets()

    assert results_one == results_two

    get_widget_spy.assert_called_once_with()


async def test_http_datasource_clears_cache_after_post(mocker, widget: Widget):
    get_widget_spy = mocker.spy(mockDB, "get_widgets")

    results_one = await widget.get_widgets()
    results_two = await widget.get_widgets()
    assert results_one == results_two
    get_widget_spy.assert_called_once_with()

    await widget.post_widget(Widgety(some="other_thing"))
    results_three = await widget.get_widgets()
    assert results_three != results_one
    assert get_widget_spy.call_count == 2


async def test_http_datasource_clears_cache_after_put(mocker, widget: Widget):
    get_widget_spy = mocker.spy(mockDB, "get_widgets")

    results_one = await widget.get_widgets()
    results_two = await widget.get_widgets()
    assert results_one == results_two
    get_widget_spy.assert_called_once_with()

    await widget.put_widget(Widgety(some="other_thing"))
    results_three = await widget.get_widgets()
    assert results_three != results_one
    assert get_widget_spy.call_count == 2


async def test_http_datasource_clears_cache_after_patch(mocker, widget: Widget):
    get_widget_spy = mocker.spy(mockDB, "get_widgets")

    results_one = await widget.get_widgets()
    results_two = await widget.get_widgets()
    assert results_one == results_two
    get_widget_spy.assert_called_once_with()

    await widget.patch_widget(Widgety(some="other_thing"))
    results_three = await widget.get_widgets()
    assert results_three != results_one
    assert get_widget_spy.call_count == 2


async def test_http_datasource_clears_cache_after_delete(mocker, widget: Widget):
    get_widget_spy = mocker.spy(mockDB, "get_widgets")

    results_one = await widget.get_widgets()
    results_two = await widget.get_widgets()
    assert results_one == results_two
    get_widget_spy.assert_called_once_with()

    await widget.delete_widget()
    results_three = await widget.get_widgets()
    assert results_three != results_one
    assert get_widget_spy.call_count == 2


async def test_http_datasource_did_receive_error(mocker, widget: Widget, mocked_client):
    mock_failer = mocker.patch.object(mocked_client, "send")
    mock_failer.side_effect = Exception("boo")

    with pytest.raises(Exception, match="boo"):
        await widget.get_widgets()


async def test_get_model_from_response_errors(widget: Widget):
    with pytest.raises(
        AttributeError,
        match="Expecting a single object in response but got list.",
    ):
        await widget.get_model_from_response_invalid()


async def test_get_model_list_from_response_errors(widget: Widget):
    with pytest.raises(
        AttributeError,
        match="Expecting a list in response but got an object.",
    ):
        await widget.get_model_list_from_response_invalid()
