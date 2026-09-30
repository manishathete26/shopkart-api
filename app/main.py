from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Integer, inspect, text

from . import models
from .api.v1.api import api_router
from .db.base import Base
from .db.session import engine

load_dotenv()

# Register all SQLAlchemy models before creating their tables.
assert models is not None
Base.metadata.create_all(bind=engine)


def update_existing_user_columns() -> None:
    """Add registration fields and migrate legacy gender strings to numeric codes."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = inspector.get_columns("users")
    existing_columns = {column["name"] for column in columns}
    gender_column = next(
        (column for column in columns if column["name"] == "gender"), None
    )
    new_columns = {
        "password_hash": "VARCHAR(512)",
        "address": "VARCHAR(500)",
        "pin": "VARCHAR(12)",
    }

    with engine.begin() as connection:
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                )

        if gender_column and not isinstance(gender_column["type"], Integer):
            if engine.dialect.name == "postgresql":
                connection.execute(text("""
                    ALTER TABLE users ALTER COLUMN gender TYPE INTEGER USING
                    CASE LOWER(gender)
                        WHEN 'male' THEN 0
                        WHEN '0' THEN 0
                        WHEN 'female' THEN 1
                        WHEN '1' THEN 1
                        WHEN 'other' THEN 2
                        WHEN 'others' THEN 2
                        WHEN '2' THEN 2
                        ELSE NULL
                    END
                """))
            else:
                connection.execute(text("""
                    UPDATE users SET gender = CASE LOWER(CAST(gender AS TEXT))
                        WHEN 'male' THEN 0
                        WHEN '0' THEN 0
                        WHEN 'female' THEN 1
                        WHEN '1' THEN 1
                        WHEN 'other' THEN 2
                        WHEN 'others' THEN 2
                        WHEN '2' THEN 2
                        ELSE NULL
                    END
                """))


update_existing_user_columns()

app = FastAPI(title="ShopKart Authentication API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://127.0.0.1:8081",
    ],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(api_router)
