import uuid

from cannula.scalars.util import JSON, UUID


def test_JSON_serialize():
    actual = JSON.serialize({"something": "clever"})
    assert actual == '{"something": "clever"}'


def test_JSON_parse_value():
    actual = JSON.parse_value('{"nothing":0}')
    assert actual == {"nothing": 0}


def test_UUID_serialize():
    uid = uuid.uuid4()
    actual = UUID.serialize(uid)
    assert actual == str(uid)


def test_UUID_parse_value():
    uid = uuid.uuid4()
    uid_str = str(uid)
    actual = UUID.parse_value(uid_str)
    assert actual == uid
