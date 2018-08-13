from west.__main__ import main
from west.db import get_current_schema_version
from west.db import is_schema_initialized


def test_version(cli_runner):
    assert cli_runner.invoke(main, ["--version"]).output == "West 0.1.0\n"


def test_current_database_state(cli_runner):

    result = cli_runner.invoke(main, [
        "--target-version",  "1.1",
        "--migrations-root",  "example_migrations",
        "migrate"])

    assert result.exit_code == 0
    assert is_schema_initialized()
    assert get_current_schema_version() == "1.1"
