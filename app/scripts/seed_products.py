"""Import or refresh the relational product catalog from app/data/products.json."""

from ..db.session import SessionLocal
from ..services.product_catalog import seed_product_catalog


def main() -> None:
    with SessionLocal() as db:
        count = seed_product_catalog(db, replace_existing=True)
    print(f"Imported {count} products and their variants from products.json")


if __name__ == "__main__":
    main()
