"""
Config
======

Simple configuration management using dotenv. This provides a
`BaseConfig` class that you can expose env vars and set defaults.

This is not as feature-full as `pydantic-settings` so use that if
you are looking for advanced features. But this will work for
simple applications like the ones we auto generate.

.. note::
    Currently only supports the following types:

    * String
    * Integer
    * Boolean

"""

import os
import typing

from dotenv import dotenv_values


def alias(env: str) -> str:
    """Set an alias for a field to override the default name.

    Example::

        class Config(BaseConfig):
            some_identifier: Annotated[str, alias("REAL_ENV_SETTING")]
    """
    return env


class BaseConfig:
    """
    Simple environment management with dotenv.

    Example::

        class Configuration(
            BaseConfig,
            prefix="APP",  # Optional prefix for env settings
            env_file=".env_secret"  # Optional setting for overriding `.env` filename
        ):
            port: int = 9000
            host: str = "0.0.0.0"
            database_uri: str = "mydb.com@user:pass"

    Then in your `.env_secret` file you can override any defaults::

        APP_PORT=8000
        APP_HOST=127.0.0.1
        APP_DATABASE_URI=something_else_here

    Your application will see the overridden values and will have the correct types::

        assert Configuration.port == 8000
        assert Configuration.host == '127.0.0.1'

    """

    _prefix: typing.ClassVar[str]
    _config: typing.ClassVar[dict[str, typing.Any]]

    def __init_subclass__(
        cls,
        prefix: typing.Optional[str] = None,
        env_file: str = ".env",
    ) -> None:
        cls._prefix = f"{prefix}_" if prefix is not None else ""
        cls._config = {
            **dotenv_values(env_file),
            **os.environ,
        }
        resolved_hints = typing.get_type_hints(cls, include_extras=True)
        for name, hint in resolved_hints.items():
            value = cls._resolve_value(hint, name, cls._prefix)
            if value is not None:
                setattr(cls, name, value)

    @classmethod
    def _resolve_value(cls, hint: typing.Any, name: str, prefix: str) -> typing.Any:
        _name = f"{prefix}{name}".upper()
        _origin = typing.get_origin(hint)

        if _origin is typing.ClassVar:
            return None

        if _origin is typing.Annotated:
            args = typing.get_args(hint)
            return cls._resolve_value(hint=args[0], name=args[1], prefix="")

        _value_set: typing.Any = None
        if hint is str:
            _value_set = cls._config.get(_name)
        elif hint is bool:
            _value_raw = cls._config.get(_name)
            if _value_raw is not None:
                _value_set = _value_raw.lower() in ["1", "on", "y", "yes", "true"]
        elif hint is int:
            _value_raw = cls._config.get(_name)
            if _value_raw is not None:
                _value_set = int(_value_raw)

        return _value_set
