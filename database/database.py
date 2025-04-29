"""
Module used to connect to the database
"""

from os import environ

import dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker, declarative_base

env = dotenv.find_dotenv()
dotenv.load_dotenv(env)

SQL_USERNAME = environ.get("DB_USERNAME")
SQL_PASSWORD = environ.get("DB_PASSWORD")
SQL_HOSTNAME = environ.get("DB_HOST")
SQL_DATABASE_NAME =environ.get("DB_NAME")


SQLALCHEMY_DATABASE_URL = URL.create(
    "postgresql",
    username=SQL_USERNAME,
    password=SQL_PASSWORD,
    host=SQL_HOSTNAME,
    database=SQL_DATABASE_NAME,
)

ENGINE = create_engine(SQLALCHEMY_DATABASE_URL)

SESSIONLOCAL = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE)

BASE = declarative_base()

def get_db():
    """
    Method used to get a database reference.
    """
    db = SESSIONLOCAL()
    try:
        yield db
    finally:
        db.close()
