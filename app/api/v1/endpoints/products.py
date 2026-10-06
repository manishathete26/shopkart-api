import json
import math
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/products", tags=["products"])

_catalog_path = Path(__file__).resolve().parents[3] / "data" / "products.json"
with _catalog_path.open(encoding="utf-8") as catalog_file:
    _catalog = json.load(catalog_file)
    _products = _catalog["products"]


@router.get("")
def list_products(
    category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: Literal["popularity", "rating", "price_asc", "price_desc"] = "popularity",
) -> dict:
    """Return a paginated, optionally filtered product list."""
    result = [
        product
        for product in _products
        if (category is None or product["category"].casefold() == category.casefold())
        and (brand is None or product["brand"].casefold() == brand.casefold())
    ]

    if sort == "rating":
        result.sort(key=lambda product: product["rating"], reverse=True)
    elif sort == "price_asc":
        result.sort(key=lambda product: product["variants"][0]["price"])
    elif sort == "price_desc":
        result.sort(key=lambda product: product["variants"][0]["price"], reverse=True)
    else:
        result.sort(key=lambda product: product["reviews"], reverse=True)

    total = len(result)
    start = (page - 1) * page_size
    page_products = result[start : start + page_size]
    return {
        "count": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": math.ceil(total / page_size) if total else 0,
        "products": page_products,
    }


@router.get("/{product_id}")
def get_product(product_id: int) -> dict:
    """Return one product by its numeric ID."""
    for product in _products:
        if product["id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")
