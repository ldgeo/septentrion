import psycopg2
import pytest


@pytest.fixture
def db():
    """
    Create a new database for running the test
    Drop it at the end
    """
    connection = psycopg2.connect(dbname="postgres")
    connection.set_session(autocommit=True)
    cursor = connection.cursor()
    test_db_name = "test_septentrion"
    # create test database to running the test
    cursor.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    cursor.execute(f"CREATE DATABASE {test_db_name}")

    params = connection.get_dsn_parameters()
    params["dbname"] = test_db_name
    yield params

    cursor.execute(f"DROP DATABASE {test_db_name}")
