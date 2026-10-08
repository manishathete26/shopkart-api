import json
import math
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....db.session import get_db
from ....models.product import Product
from ....services.product_catalog import product_to_dict

router = APIRouter(tags=["catalog"])

_catalog_path = Path(__file__).resolve().parents[3] / "data" / "products.json"
with _catalog_path.open(encoding="utf-8") as catalog_file:
    _catalog = json.load(catalog_file)
    _categories = _catalog["categories"]
    _deal_entries = _catalog["bestDeals"]


def _get_deals(db: Session) -> list[dict]:
    deal_ids = [deal["productId"] for deal in _deal_entries]
    products = db.scalars(
        select(Product).where(Product.id.in_(deal_ids))
    ).all()
    products_by_id = {product.id: product for product in products}
    deals = []
    for deal in _deal_entries:
        product = products_by_id.get(deal["productId"])
        if product:
            deals.append({**product_to_dict(product), "deal": deal})
    return deals


@router.get("/home")
def get_home_page(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    """Return all home-page content and a paginated product list in one response."""
    products = db.scalars(
        select(Product).order_by(Product.id)
    ).all()
    deals = _get_deals(db)
    start = (page - 1) * page_size
    page_products = [product_to_dict(p) for p in products[start : start + page_size]]
    return {
        "topCategories": _categories,
        "bestDeals": deals,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalProducts": len(products),
            "totalPages": math.ceil(len(products) / page_size),
        },
        "products": page_products,
    }
