import json
from pathlib import Path

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from ..models.product import Product

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "products.json"


def read_catalog() -> dict:
    with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
        return json.load(catalog_file)


def seed_product_catalog(db: Session, *, replace_existing: bool = False) -> int:
    """Load products.json into products rows with embedded variant JSON.

    By default this is an initial seed and leaves an already-populated catalog alone.
    Set replace_existing=True from the explicit seed command to sync the JSON catalog.
    """
    product_count = db.scalar(select(func.count()).select_from(Product)) or 0
    if product_count and not replace_existing:
        return 0

    catalog = read_catalog()
    for product_data in catalog.get("products", []):
        product_id = int(product_data["id"])
        product = db.get(Product, product_id)
        if product is None:
            product = Product(id=product_id)
            db.add(product)

        product.name = product_data["name"]
        product.description = product_data.get("description")
        product.category = product_data["category"]
        product.sub_category = product_data.get("subCategory")
        product.brand = product_data.get("brand")
        product.rating = product_data.get("rating")
        product.reviews = int(product_data.get("reviews", 0))
        product.offers = product_data.get("offers", [])
        product.badge = product_data.get("badge")
        product.variants = product_data.get("variants", [])

    db.commit()
    return len(catalog.get("products", []))


def product_to_dict(product: Product) -> dict:
    """Serialize a database product to the existing API's camelCase JSON shape."""
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "subCategory": product.sub_category,
        "brand": product.brand,
        "rating": product.rating,
        "reviews": product.reviews,
        "offers": product.offers or [],
        "variants": product.variants or [],
        "badge": product.badge,
    }


def migrate_legacy_variants(engine) -> None:
    """Copy normalized variant rows into products.variants for old databases.

    This keeps the old table as a backup. It is not used by the API after this
    migration; users can drop it manually after verifying the copied data.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "products" not in tables:
        return

    product_columns = {column["name"] for column in inspector.get_columns("products")}
    added_variants_column = "variants" not in product_columns
    if added_variants_column:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE products ADD COLUMN variants JSON"))
            connection.execute(text("UPDATE products SET variants = '[]' WHERE variants IS NULL"))

    if "product_variants" not in tables or not added_variants_column:
        return

    with engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT variantid, parent_id, variant_product_id, slug, options,
                   price, originalPrice, stock, images
            FROM product_variants
            ORDER BY parent_id, variantid
        """)).mappings().all()

    grouped: dict[int, list[dict]] = {}
    for row in rows:
        def as_json(value):
            return json.loads(value) if isinstance(value, str) else value

        parent_id = int(row["parent_id"])
        grouped.setdefault(parent_id, []).append({
            "variantid": row["variantid"],
            "productId": row["variant_product_id"],
            "parentId": parent_id,
            "slug": row["slug"],
            "options": as_json(row["options"]) or [],
            "price": row["price"],
            "originalPrice": row["originalPrice"],
            "stock": row["stock"],
            "images": as_json(row["images"]) or [],
        })

    with Session(engine) as db:
        for product_id, variants in grouped.items():
            product = db.get(Product, product_id)
            if product is not None:
                product.variants = variants
        db.commit()
