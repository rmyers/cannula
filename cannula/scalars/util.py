import json
import uuid

from ._base import ScalarType


class JSON(ScalarType[dict, str]):

    @staticmethod
    def serialize(value: dict) -> str:
        return json.dumps(value)

    @staticmethod
    def parse_value(value: str) -> dict:
        return json.loads(value)


class UUID(ScalarType[uuid.UUID, str]):

    @staticmethod
    def serialize(value: uuid.UUID) -> str:
        return str(value)

    @staticmethod
    def parse_value(value: str) -> uuid.UUID:
        return uuid.UUID(value)
