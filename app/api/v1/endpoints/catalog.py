import json
import random
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(tags=["catalog"])

_catalog_path = Path(__file__).resolve().parents[3] / "data" / "products.json"
with _catalog_path.open(encoding="utf-8") as catalog_file:
    _catalog = json.load(catalog_file)
    _categories = _catalog["categories"]
    _deal_entries = _catalog["bestDeals"]
    _products = _catalog["products"]
    _products_by_id = {product["id"]: product for product in _products}


def _get_deals() -> list[dict]:
    deals = []
    for deal in _deal_entries:
        product = _products_by_id.get(deal["productId"])
        if product:
            deals.append({**product, "deal": deal})
    return deals


@router.get("/categories")
def list_categories() -> dict:
    """Return the categories shown on the home page."""
    return {"count": len(_categories), "categories": _categories}


@router.get("/deals")
def list_best_deals() -> dict:
    """Return the curated best-deal products."""
    deals = _get_deals()
    return {"count": len(deals), "bestDeals": deals}


@router.get("/home")
def get_home_page(products_per_category: int = Query(default=4, ge=1, le=20)) -> dict:
    """Return categories, best deals, and random products for each category."""
    deals = _get_deals()
    products_by_category = []
    for category in _categories:
        category_name = category["name"] if isinstance(category, dict) else category
        matching_products = [
            product
            for product in _products
            if product["category"].casefold() == category_name.casefold()
        ]
        products_by_category.append(
            {
                "category": category,
                "products": random.sample(
                    matching_products,
                    min(products_per_category, len(matching_products)),
                ),
            }
        )
    return {
        "topCategories": _categories,
        "bestDeals": deals,
        "productsByCategory": products_by_category,
    }
