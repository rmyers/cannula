import sys

import pytest
from pytest_mock import MockerFixture

from cannula.cli import main


def test_help(mocker: MockerFixture):
    mocker.patch.object(sys, "argv", ["cli", "--help"])
    with pytest.raises(SystemExit):
        main()


def test_invalid_command_does_not_hang(mocker: MockerFixture):
    mocker.patch("cannula.render_file")
    mocker.patch.object(sys, "argv", ["cli", "codegen", "schema", "--invalid"])
    main()


def test_codegen(mocker: MockerFixture):
    mock_schema = mocker.Mock()
    mocker.patch("cannula.load_schema", return_value=mock_schema)
    mock_render = mocker.patch("cannula.render_file")
    mocker.patch.object(sys, "argv", ["cli", "codegen", "schema.grapql"])
    main()
    mock_render.assert_called_with(
        type_defs=mock_schema,
        path=mocker.ANY,
        dry_run=False,
    )


def test_codegen_dry_run(mocker: MockerFixture):
    mock_schema = mocker.Mock()
    mocker.patch("cannula.load_schema", return_value=mock_schema)
    mock_render = mocker.patch("cannula.render_file")
    mocker.patch.object(sys, "argv", ["cli", "--dry-run", "codegen", "schema.grapql"])
    main()
    mock_render.assert_called_with(
        type_defs=mock_schema,
        path=mocker.ANY,
        dry_run=True,
    )
