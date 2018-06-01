"""
Interact with the migrations table.
"""

from contextlib import contextmanager
from distutils.version import StrictVersion

import psycopg2
from psycopg2.extras import DictCursor

from west.settings import settings


def get_connection():
    return psycopg2.connect(
        host=settings.HOST,
        port=settings.PORT,
        dbname=settings.DBNAME,
        user=settings.USERNAME,
        password=settings.PASSWORD)


@contextmanager
def execute(query, args=tuple(), commit=False):
    query = ' '.join(query.format(table=settings.TABLE).split())
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, args)
            yield cur
        if commit:
            conn.commit()


class Query(object):
    def __init__(self, query, args=tuple(), commit=False):
        self.context_manager = execute(query, args, commit)

    def __enter__(self):
        return self.context_manager.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.context_manager.__exit__(exc_type, exc_val, exc_tb)

    def __call__(self):
        with self:
            pass


query_create_table = """
CREATE TABLE IF NOT EXISTS "{table}" (
    id BIGSERIAL PRIMARY KEY,
    version TEXT,
    name TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
"""

query_max_version = """SELECT DISTINCT "version" FROM "{table}" """

query_write_migration = """
    INSERT INTO "{table}" ("version", "name")
    VALUES (%s, %s)
"""

query_get_applied_migrations = """
    SELECT name FROM "{table}" WHERE "version" = %s
"""


def get_schema_version():
    versions = get_applied_versions()
    if not versions:
        return None
    return max(StrictVersion(version)
               for version in versions)


def get_applied_versions():
    with Query(query_max_version) as cur:
        return [row[0] for row in cur]


def get_applied_migrations(version):
    with Query(query_get_applied_migrations, version) as cur:
        return [row[0] for row in cur]


def create_table():
    Query(query_create_table,
          commit=True)()


def write_migration(version, name):
    Query(query_write_migration,
          (version, name),
          commit=True)()
