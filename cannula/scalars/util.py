import json
import uuid

from ._base import ScalarType


class JSON(ScalarType[dict, str]):
    """JSON seralizes to :func:`json` objects"""

    @staticmethod
    def serialize(value: dict) -> str:
        return json.dumps(value)

    @staticmethod
    def parse_value(value: str) -> dict:
        return json.loads(value)


class UUID(ScalarType[uuid.UUID, str]):
    """UUID seralizes to :func:`uuid.UUID` objects"""

    @staticmethod
    def serialize(value: uuid.UUID) -> str:
        return str(value)

    @staticmethod
    def parse_value(value: str) -> uuid.UUID:
        return uuid.UUID(value)
