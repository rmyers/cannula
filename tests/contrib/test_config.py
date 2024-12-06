import os
from typing import Annotated

from cannula.contrib import config


def test_config_alias(mocker):
    mocker.patch.dict(
        os.environ,
        {
            "TEST_OTHER": "lame",
            "TEST_PORT": "not-this",
            "REAL_PORT": "12345",
            "TEST_IS_DEV": "true",
        },
    )

    class Config(config.BaseConfig, prefix="TEST"):

        port: Annotated[int, config.alias("REAL_PORT")]
        other: str = "value"
        is_dev: bool = False

    assert Config.other == "lame"
    assert Config.port == 12345
    assert Config.is_dev is True
