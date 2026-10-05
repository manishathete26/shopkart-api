import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from ...deps import get_current_user

router = APIRouter(
    prefix="/products",
    tags=["products"],
    dependencies=[Depends(get_current_user)],
)

_catalog_path = Path(__file__).resolve().parents[3] / "data" / "products.json"
with _catalog_path.open(encoding="utf-8") as catalog_file:
    _products = json.load(catalog_file)["products"]


@router.get("")
def list_products(
    category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
) -> dict:
    """Return products, optionally filtered by category and brand."""
    result = [
        product
        for product in _products
        if (category is None or product["category"].casefold() == category.casefold())
        and (brand is None or product["brand"].casefold() == brand.casefold())
    ]
    return {"count": len(result), "products": result}


@router.get("/{product_id}")
def get_product(product_id: int) -> dict:
    """Return one product by its numeric ID."""
    for product in _products:
        if product["id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")
