from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import inspect, text

from . import models
from .api.v1.api import api_router
from .db.base import Base
from .db.session import engine

load_dotenv()

# models is imported for its side effect: registering SQLAlchemy tables with
# Base.metadata before the tables are created.
assert models is not None

Base.metadata.create_all(bind=engine)


def add_missing_registration_columns() -> None:
    """Add the new nullable registration fields to an existing users table."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    new_columns = {
        "password_hash": "VARCHAR(512)",
        "address": "VARCHAR(500)",
        "pin": "VARCHAR(12)",
    }

    with engine.begin() as connection:
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
                    )
                )


add_missing_registration_columns()

app = FastAPI(title="ShopKart Authentication API", version="1.0.0")
app.include_router(api_router)
