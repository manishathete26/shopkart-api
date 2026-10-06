import json
import math
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


@router.get("/home")
def get_home_page(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Return all home-page content and a paginated product list in one response."""
    deals = _get_deals()
    start = (page - 1) * page_size
    page_products = _products[start : start + page_size]
    return {
        "topCategories": _categories,
        "bestDeals": deals,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalProducts": len(_products),
            "totalPages": math.ceil(len(_products) / page_size),
        },
        "products": page_products,
    }
