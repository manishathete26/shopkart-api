import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.product import Product, ProductVariant

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "products.json"


def read_catalog() -> dict:
    with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
        return json.load(catalog_file)


def seed_product_catalog(db: Session, *, replace_existing: bool = False) -> int:
    """Load products.json into relational product and variant tables.

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
        product.variants = [
            ProductVariant(
                variantid=str(
                    variant.get("variantid")
                    or variant.get("id")
                    or f"{product_id}-{index}"
                ),
                variant_product_id=int(variant.get("productId", product_id)),
                slug=variant.get("slug", ""),
                options=variant.get("options", []),
                price=int(variant["price"]),
                original_price=int(variant.get("originalPrice", variant["price"])),
                stock=int(variant.get("stock", 0)),
                images=variant.get("images", []),
            )
            for index, variant in enumerate(product_data.get("variants", []), start=1)
        ]

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
        "variants": [
            {
                "variantid": variant.variantid,
                "productId": variant.variant_product_id,
                "parentId": variant.parent_id,
                "slug": variant.slug,
                "options": variant.options or [],
                "price": variant.price,
                "originalPrice": variant.original_price,
                "stock": variant.stock,
                "images": variant.images or [],
            }
            for variant in product.variants
        ],
        "badge": product.badge,
    }
