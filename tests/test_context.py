from fastapi import Request

from cannula import context, CannulaAPI


async def test_custom_context(valid_schema, valid_query):
    class MyContext(context.Context[Request]):
        my_attribute: str = "hard coded name"

    def get_me(info: context.ResolveInfo[MyContext]):
        return {"name": info.context.my_attribute}

    root_value = {"me": get_me}

    api = CannulaAPI(valid_schema, context=MyContext, root_value=root_value)

    results = await api.call(valid_query)
    assert results.data
    assert results.data.get("me") == {"name": "hard coded name"}
