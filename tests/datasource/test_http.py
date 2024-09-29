import httpx
import fastapi

from cannula.datasource import http


class MockDB:
    # This is just a object that we can use in assertions
    # that it was called the specific number of times
    def get_widgets(self):
        return [{"some": "thing"}]


mockDB = MockDB()
fake_app = fastapi.FastAPI()


@fake_app.get("/widgets")
async def widget():
    return mockDB.get_widgets()


async def test_http_datasource(mocker):
    class Widget(http.HTTPDataSource):
        base_url = "http://localhost/"

        async def get_widgets(self):
            return await self.get("widgets")

    get_widget_spy = mocker.spy(mockDB, "get_widgets")
    mocked_client = httpx.AsyncClient(transport=httpx.ASGITransport(app=fake_app))
    widget = Widget(request=mocker.Mock(), client=mocked_client)

    results_one = await widget.get_widgets()
    results_two = await widget.get_widgets()

    assert results_one == results_two
    assert isinstance(results_one, list)
    assert results_one[0].some == "thing"

    get_widget_spy.assert_called_once_with()
