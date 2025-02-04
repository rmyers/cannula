async def test_hello_world():
    from tests.fixtures.examples import hello

    results = await hello.run_hello("sammy")  # type: ignore
    assert results == {"hello": "hello sammy!"}


async def test_extension_works_properly_from_multiple_file():
    from tests.fixtures.examples.extension import main

    results = await main.api.call(main.QUERY)
    assert results.data == {
        "books": [
            {
                "author": "Frank",
                "movies": [{"director": "Ted", "name": "Lost the Movie"}],
                "name": "Lost",
            }
        ],
        "media": [
            {
                "__typename": "Book",
                "author": "Jane",
                "name": "the Best Movies",
            },
            {
                "__typename": "Movie",
                "director": "Sally",
                "name": "the Best Books",
            },
        ],
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


async def test_scalars():
    from tests.fixtures.examples.scalars import main

    results = await main.api.call(main.QUERY)
    assert results is not None
    assert results.errors is None
    assert results.data == {
        "scaled": {
            "birthday": "2019-03-08",
            "created": "2024-02-05T06:47:00",
            "id": "e0c2c649-9c66-4f55-a2d4-966cc4f7d186",
            "meta": '{"fancy": "pants"}',
            "smoke": "04:20:00",
        }
    }


async def test_orm_datasource():
    from tests.fixtures.examples.datasources import orm

    results = await orm.main()
    assert results is not None
    assert results.errors is None
    assert results.data == {
        "user": {
            "widgets": [
                {"name": "Hammer"},
                {"name": "Drill"},
                {"name": "Nail"},
            ],
        },
        "another": {
            "widgets": [
                {"name": "Hammer"},
                {"name": "Drill"},
                {"name": "Nail"},
            ],
        },
    }


async def test_http_datasource():
    from tests.fixtures.examples.datasources import http

    results = await http.main()
    assert results is not None
    assert results.errors is None
    assert results.data == {
        "user": {
            "widgets": [
                {"name": "Hammer"},
                {"name": "Drill"},
                {"name": "Nail"},
            ],
        },
        "another": {
            "widgets": [
                {"name": "Hammer"},
                {"name": "Drill"},
                {"name": "Nail"},
            ],
        },
    }
