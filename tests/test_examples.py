async def test_hello_world():
    from tests.fixtures.examples import hello

    results = await hello.run_hello("sammy")  # type: ignore
    assert results == {"hello": "hello sammy!"}


def test_extension_works_properly_from_multiple_file():
    from tests.fixtures.examples.extension import main

    results = main.api.call_sync(main.QUERY)
    assert results.data == {
        "books": [
            {
                "author": "Frank",
                "movies": [{"director": "Ted", "name": "Lost the Movie"}],
                "name": "Lost",
            }
        ]
    }


def test_mocks_work_properly():
    from tests.fixtures.examples import mocks

    # all values are mocked
    default_results = mocks.default.call_sync(mocks.sample_query)
    assert default_results.data
    mock_result = default_results.data["mockity"][0]
    assert isinstance(mock_result["text"], str)
    assert isinstance(mock_result["number"], int)
    assert isinstance(mock_result["float"], float)
    assert isinstance(mock_result["isOn"], bool)
    assert isinstance(mock_result["id"], str)

    # some values are constant while the rest are mocked
    custom_results = mocks.custom.call_sync(mocks.sample_query)
    assert custom_results.data
    mock_result = custom_results.data["mockity"][0]
    # we need to remove the mocked values
    assert isinstance(mock_result.pop("id"), str)
    assert isinstance(mock_result.pop("float"), float)
    assert isinstance(mock_result.pop("isOn"), bool)
    # assert the rest is the custom values we set
    assert mock_result == {
        "text": "This will be used for all Strings",
        "number": 42,
        "brocoli": {"taste": "Delicious"},
    }

    # limited mocks only return the custom values
    limited_results = mocks.limited_mocks.call_sync(mocks.sample_query)
    assert limited_results.data
    mock_result = limited_results.data["mockity"][0]
    assert mock_result == {
        "text": "This will be used for all Strings",
        "number": 42,
        "float": None,
        "id": None,
        "isOn": False,
        "brocoli": {"taste": "Delicious"},
    }


async def test_http_datasource():
    from tests.fixtures.examples import http_datasource

    results = await http_datasource.main()
    assert results is not None
    assert results == {
        "widgets": [{"name": "hammer", "type": "tool"}],
        "another": [{"name": "hammer", "type": "tool"}],
    }


async def test_profiler():
    from tests.fixtures.examples import profiler

    results = await profiler.main()
    assert results is not None
    assert results.errors is None
    assert results.data == {
        "prime": "17624813 is a prime number",
        "hello": "hello World!",
    }
