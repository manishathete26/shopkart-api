import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["catalog"])

_catalog_path = Path(__file__).resolve().parents[3] / "data" / "products.json"
with _catalog_path.open(encoding="utf-8") as catalog_file:
    _catalog = json.load(catalog_file)
    _categories = _catalog["categories"]
    _deal_entries = _catalog["bestDeals"]
    _products_by_id = {product["id"]: product for product in _catalog["products"]}


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
def get_home_page() -> dict:
    """Return the home-page categories and best deals in one response."""
    deals = _get_deals()
    return {
        "topCategories": _categories,
        "bestDeals": deals,
    }
