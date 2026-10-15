import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....db.session import get_db
from ....models.product import Product
from ....services.product_catalog import product_to_dict

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(
    search: str | None = Query(default=None, min_length=1),
    category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0, alias="minPrice"),
    max_price: float | None = Query(default=None, ge=0, alias="maxPrice"),
    rating: float | None = Query(default=None, ge=0, le=5),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: Literal["popularity", "rating", "price_asc", "price_desc"] = "popularity",
    db: Session = Depends(get_db),
) -> dict:
    """Return a paginated, optionally filtered product list."""
    products = db.scalars(select(Product)).all()

    def prices_for(product: Product) -> list[float]:
        prices = []
        for variant in product.variants or []:
            try:
                price = float(variant.get("price", 0))
            except (TypeError, ValueError):
                continue
            if math.isfinite(price) and price >= 0:
                prices.append(price)
        return prices

    normalized_search = search.strip().casefold() if search else None
    result = [
        product
        for product in products
        if (category is None or product.category.casefold() == category.casefold())
        and (brand is None or (product.brand or "").casefold() == brand.casefold())
        and (
            normalized_search is None
            or normalized_search in " ".join(
                filter(None, [product.name, product.description, product.category, product.brand])
            ).casefold()
        )
        and (rating is None or (product.rating or 0) >= rating)
        and (min_price is None or any(price >= min_price for price in prices_for(product)))
        and (max_price is None or any(price <= max_price for price in prices_for(product)))
        and (
            min_price is None
            or max_price is None
            or any(min_price <= price <= max_price for price in prices_for(product))
        )
    ]

    if sort == "rating":
        result.sort(key=lambda product: product.rating or 0, reverse=True)
    elif sort == "price_asc":
        result.sort(key=lambda product: min(prices_for(product), default=0))
    elif sort == "price_desc":
        result.sort(
            key=lambda product: min(prices_for(product), default=0),
            reverse=True,
        )
    else:
        result.sort(key=lambda product: product.reviews, reverse=True)

    total = len(result)
    start = (page - 1) * page_size
    page_products = [product_to_dict(p) for p in result[start : start + page_size]]
    return {
        "count": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": math.ceil(total / page_size) if total else 0,
        "products": page_products,
    }


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)) -> dict:
    """Return one product by its numeric ID."""
    product = db.scalar(
        select(Product)
        .where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_to_dict(product)
