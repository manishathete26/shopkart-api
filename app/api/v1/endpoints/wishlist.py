import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ....api.deps import get_current_user
from ....db.session import get_db
from ....models.auth import User
from ....models.wishlist import WishlistItem
from ....schemas.wishlist import WishlistAddRequest

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

_catalog_path = Path(__file__).resolve().parents[3] / "data" / "products.json"
with _catalog_path.open(encoding="utf-8") as catalog_file:
    _products = json.load(catalog_file)["products"]
    _products_by_id = {product["id"]: product for product in _products}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    payload: WishlistAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Add a catalog product to the authenticated user's wishlist."""
    if payload.product_id not in _products_by_id:
        raise HTTPException(status_code=404, detail="Product not found")

    existing = db.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == payload.product_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Product is already in your wishlist")

    item = WishlistItem(user_id=current_user.id, product_id=payload.product_id)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Product is already in your wishlist",
        ) from error

    db.refresh(item)
    return {
        "message": "Product added to wishlist",
        "wishlist_item_id": item.id,
        "product_id": item.product_id,
    }


@router.get("")
def get_wishlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the authenticated user's wishlist with the current catalog details."""
    items = db.scalars(
        select(WishlistItem)
        .where(WishlistItem.user_id == current_user.id)
        .order_by(WishlistItem.id.desc())
    ).all()

    return {
        "count": len(items),
        "items": [
            {
                "wishlist_item_id": item.id,
                "product_id": item.product_id,
                "product": _products_by_id.get(item.product_id),
            }
            for item in items
        ],
    }


@router.delete("/{product_id}")
def remove_from_wishlist(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Remove a product only from the authenticated user's wishlist."""
    item = db.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == product_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Wishlist item not found")

    db.delete(item)
    db.commit()
    return {"message": "Product removed from wishlist", "product_id": product_id}
