import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth.db")

# Render may provide the legacy "postgres://" URL scheme.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# This project installs psycopg2-binary, so select its SQLAlchemy driver explicitly.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )

# SQLAlchemy needs the PyMySQL dialect driver for MySQL connection URLs.
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def ensure_wishlist_product_foreign_key() -> None:
    """Add the product FK to existing MySQL/PostgreSQL wishlist tables.

    create_all creates the constraint for new databases but does not alter an
    existing wishlist_items table. SQLite cannot add a foreign key with ALTER
    TABLE, so existing SQLite files require a table rebuild to gain the FK.
    """
    if engine.dialect.name not in {"mysql", "postgresql"}:
        return

    inspector = inspect(engine)
    if "wishlist_items" not in inspector.get_table_names():
        return
    for foreign_key in inspector.get_foreign_keys("wishlist_items"):
        if foreign_key.get("referred_table") == "products":
            return

    with engine.begin() as connection:
        orphan = connection.execute(text("""
            SELECT wishlist_items.product_id
            FROM wishlist_items
            LEFT JOIN products ON products.id = wishlist_items.product_id
            WHERE products.id IS NULL
            LIMIT 1
        """)).first()
        if orphan:
            raise RuntimeError(
                "Cannot add the wishlist product foreign key: "
                f"wishlist product_id {orphan[0]} does not exist in products. "
                "Repair or remove that wishlist row, then restart the API."
            )

        connection.execute(text("""
            ALTER TABLE wishlist_items
            ADD CONSTRAINT fk_wishlist_items_product_id_products
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
        """))


def ensure_wishlist_variant_column() -> None:
    """Add variant_id to wishlist rows created by older application versions."""
    inspector = inspect(engine)
    if "wishlist_items" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("wishlist_items")}
    if "variant_id" in columns:
        return

    # Nullable keeps existing wishlist entries valid because their former
    # product-only records did not retain a selected variant.
    with engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE wishlist_items ADD COLUMN variant_id VARCHAR(255) NULL"
        ))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
