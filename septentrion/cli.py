"""
All things related to the CLI and only that. This module can call functions
from other modules to get the information it needs, then format it and display
it.
"""
import functools
import logging
import os
from typing import Any, TextIO

import click
from click.types import StringParamType

from septentrion import (
    __version__,
    configuration,
    core,
    db,
    exceptions,
    migrate,
    style,
    utils,
)

logger = logging.getLogger(__name__)


click.option = functools.partial(click.option, show_default=True)  # type: ignore


def load_config(ctx: click.Context, param: click.Parameter, value: TextIO) -> None:
    if not value:
        try:
            file_contents, file = configuration.read_default_configuration_files()
        except exceptions.NoDefaultConfiguration:
            pass
    else:
        file = getattr(value, "name", "stdin")
        logger.info(f"Reading configuration from {file}")
        file_contents = value.read()

    try:
        default = configuration.parse_configuration_file(file_contents)
    except exceptions.NoSeptentrionSection:
        if file in configuration.CONFIGURATION_FILES:
            click.echo(
                f"Configuration file found at {file} but contains no septentrion "
                "section"
            )
        default = {}

    ctx.default_map = default


CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "auto_envvar_prefix": "SEPTENTRION",
    "max_content_width": 120,
}


def validate_version(ctx: click.Context, param: Any, value: str):
    if value and not utils.is_version(value):
        raise click.BadParameter(f"{value} is not a valid version")
    return value


class CommaSeparatedMultipleString(StringParamType):
    envvar_list_splitter = ","

    def split_envvar_value(self, rv: str):
        values = super(CommaSeparatedMultipleString, self).split_envvar_value(rv)
        return tuple(value.strip() for value in values)


@click.group(
    context_settings=CONTEXT_SETTINGS,
    help="""
    Septentrion is a command line tool to manage execution of PostgreSQL
    migrations. It uses a migration table to synchronize migration
    execution.
    """,
)
@click.pass_context
@click.option(
    "--config-file",
    is_eager=True,
    callback=load_config,
    help="Config file to use (env: SEPTENTRION_CONFIG_FILE)  "
    f"[default: {' or '.join(configuration.CONFIGURATION_FILES)}]",
    type=click.File("rb"),
)
@click.version_option(__version__, "-V", "--version", prog_name="septentrion")
@click.option("-v", "--verbose", count=True)
@click.option("--host", "-H", help="Database host (env: SEPTENTRION_HOST or PGHOST)")
@click.option("--port", "-p", help="Database port (env: SEPTENTRION_PORT or PGPORT)")
@click.option(
    "--username", "-U", help="Database host (env: SEPTENTRION_USERNAME or PGUSER)"
)
@click.option(
    "--password/--no-password",
    "-W/-w",
    "password_flag",
    help="Prompt for the database password, otherwise read from environment variable "
    "PGPASSWORD, SEPTENTRION_PASSWORD, or ~/.pgpass",
    envvar=None,
)
@click.option(
    "--dbname", "-d", help="Database name (env: SEPTENTRION_DBNAME or PGDATABASE)"
)
@click.option(
    "--table",
    help="Database table in which to write migrations. The table will be created "
    "immediately if it doesn't exist (env: SEPTENTRION_TABLE)",
    default=configuration.DEFAULTS["table"],
)
@click.option(
    "--migrations-root",
    help="Path to the migration files (env: SEPTENTRION_MIGRATION_ROOT)",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    default=configuration.DEFAULTS["migrations_root"],
)
@click.option(
    "--target-version",
    help="Desired final version of the Database (env: SEPTENTRION_TARGET_VERSION)",
    callback=validate_version,
    required=True,
)
@click.option(
    "--schema-version",
    help="Version of the initial schema (if not specified, the most resent schema "
    "will be used) (env: SEPTENTRION_SCHEMA_VERSION)",
    callback=validate_version,
)
@click.option(
    "--schema-template",
    help="Template name for schema files " "(env: SEPTENTRION_SCHEMA_TEMPLATE)",
    default=configuration.DEFAULTS["schema_template"],
)
@click.option(
    "--fixtures-template",
    help="Template name for schema files " "(env: SEPTENTRION_FIXTURES_TEMPLATE)",
    default=configuration.DEFAULTS["fixtures_template"],
)
@click.option(
    "--non-transactional-keyword",
    multiple=True,
    type=CommaSeparatedMultipleString(),
    help="When those words are found in the migration, it is executed outside of a "
    "transaction (repeat the flag as many times as necessary) "
    "(env: SEPTENTRION_NON_TRANSACTIONAL_KEYWORD, comma separated values)",
    default=configuration.DEFAULTS["non_transactional_keyword"],
)
@click.option(
    "--additional-schema-file",
    multiple=True,
    type=CommaSeparatedMultipleString(),
    help="Path to a SQL file relative to <migration-root>/schemas, to be run in "
    "addition to the migrations, e.g for installing postgres extensions (repeat the "
    "flag as many times as necessary) (env: SEPTENTRION_ADDITIONAL_SCHEMA_FILE, comma "
    "separated values)",
)
def cli(ctx: click.Context, **kwargs):
    if kwargs.pop("password_flag"):
        password = click.prompt("Database password", hide_input=True)
    else:
        password = os.getenv("SEPTENTRION_PASSWORD")
    kwargs["password"] = password

    ctx.obj = settings = configuration.Settings.from_cli(kwargs)

    # All other commands will need the table to be created
    logger.info("Ensuring migration table exists")
    # TODO: this probably deserves an option
    db.create_table(settings=settings)  # idempotent


@cli.command(name="show-migrations")
@click.pass_obj
def show_migrations(settings: configuration.Settings):
    """
    Show the current state of the database.
    Retrieves informations on the current version
    of the database schema, and the applied and
    unapplied migrations.
    """
    core.describe_migration_plan(settings=settings, stylist=style.stylist)


@cli.command(name="migrate")
@click.pass_obj
def migrate_func(settings: configuration.Settings):
    """
    Run unapplied migrations.

    """
    migrate.migrate(settings=settings, stylist=style.stylist)


@cli.command()
@click.argument("version", callback=validate_version)
@click.pass_obj
def fake(settings: configuration.Settings, version: str):
    """
    Fake migrations until version.
    Write migrations in the migration table without applying them, for
    all migrations up until the given version (included). This is useful
    when installing septentrion on an existing DB.
    """
    migrate.create_fake_entries(settings=settings, version=version)
