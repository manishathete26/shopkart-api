from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ....api.deps import get_current_user
from ....db.session import get_db
from ....models.auth import User
from ....models.cart import CartItem
from ....models.product import Product
from ....models.wishlist import WishlistItem
from ....schemas.wishlist import WishlistAddRequest
from ....services.product_catalog import product_to_dict
from .cart import cart_response, get_variant_price_and_stock

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


def find_variant(product: Product, variant_id: str) -> dict:
    for variant in product.variants or []:
        if str(variant.get("variantid", "")) == variant_id:
            return variant
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")


@router.post("", status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    payload: WishlistAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Add a catalog product to the authenticated user's wishlist."""
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    find_variant(product, payload.variant_id)

    existing = db.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == payload.product_id,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product is already in your wishlist")

    item = WishlistItem(
        user_id=current_user.id,
        product_id=payload.product_id,
        variant_id=payload.variant_id,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is already in your wishlist",
        ) from error

    db.refresh(item)
    return {
        "message": "Product added to wishlist",
        "wishlist_item_id": item.id,
        "product_id": item.product_id,
        "variant_id": item.variant_id,
    }


@router.get("")
def get_wishlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the authenticated user's wishlist with the current catalog details."""
    items = db.scalars(
        select(WishlistItem)
        .options(selectinload(WishlistItem.product))
        .where(WishlistItem.user_id == current_user.id)
        .order_by(WishlistItem.id.desc())
    ).all()

    return {
        "count": len(items),
        "items": [
            {
                "wishlist_item_id": item.id,
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "variant": (
                    find_variant(item.product, item.variant_id)
                    if item.product is not None and item.variant_id is not None
                    else None
                ),
                "product": (
                    product_to_dict(item.product) if item.product is not None else None
                ),
            }
            for item in items
        ],
    }


@router.post("/{product_id}/cart")
def move_wishlist_item_to_cart(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Move a saved product variant into the authenticated user's cart."""
    wishlist_item = db.scalar(
        select(WishlistItem)
        .where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.product_id == product_id,
        )
        .with_for_update()
    )
    if wishlist_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")
    if not wishlist_item.variant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Choose a product variant before moving this item to the cart",
        )

    product = db.get(Product, wishlist_item.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    _, _, stock = get_variant_price_and_stock(product, wishlist_item.variant_id)
    cart_item = db.scalar(
        select(CartItem)
        .where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == product_id,
            CartItem.variant_id == wishlist_item.variant_id,
        )
        .with_for_update()
    )
    new_quantity = (cart_item.quantity if cart_item else 0) + 1
    if stock == 0 or new_quantity > stock or new_quantity > 99:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requested quantity is not available in stock",
        )

    if cart_item:
        cart_item.quantity = new_quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            variant_id=wishlist_item.variant_id,
            quantity=1,
        )
        db.add(cart_item)

    wishlist_item_id = wishlist_item.id
    variant_id = wishlist_item.variant_id
    db.delete(wishlist_item)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Wishlist item could not be moved to the cart",
        ) from error

    db.refresh(cart_item)
    return {
        "message": "Wishlist item moved to cart",
        "wishlist_item_id": wishlist_item_id,
        "item_id": cart_item.id,
        "product_id": product_id,
        "variant_id": variant_id,
        **cart_response(db, current_user.id),
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")

    db.delete(item)
    db.commit()
    return {"message": "Product removed from wishlist", "product_id": product_id}
