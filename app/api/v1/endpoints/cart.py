from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ....api.deps import get_current_user
from ....db.session import get_db
from ....models.auth import User
from ....models.cart import CartItem
from ....models.product import Product
from ....schemas.cart import CartItemCreate, CartItemUpdate

router = APIRouter(prefix="/cart", tags=["cart"])


def find_variant(product: Product, variant_id: str) -> dict:
    for variant in product.variants or []:
        if str(variant.get("variantid", "")) == variant_id:
            return variant
    raise HTTPException(status_code=404, detail="Product variant not found")


def get_variant_price_and_stock(product: Product, variant_id: str) -> tuple[dict, Decimal, int]:
    variant = find_variant(product, variant_id)
    try:
        price = Decimal(str(variant["price"]))
        stock = int(variant.get("stock", 0))
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=409, detail="Product variant has invalid price or stock")
    if not price.is_finite() or price < 0 or stock < 0:
        raise HTTPException(status_code=409, detail="Product variant has invalid price or stock")
    return variant, price, stock


def cart_response(db: Session, user_id: int) -> dict:
    rows = db.execute(
        select(CartItem, Product)
        .join(Product, Product.id == CartItem.product_id)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.id)
    ).all()

    items = []
    cart_total = Decimal("0")
    total_quantity = 0
    for item, product in rows:
        variant, unit_price, _ = get_variant_price_and_stock(product, item.variant_id)
        line_total = unit_price * item.quantity
        cart_total += line_total
        total_quantity += item.quantity
        items.append({
            "item_id": item.id,
            "product_id": product.id,
            "product_name": product.name,
            "variant_id": item.variant_id,
            "variant": variant,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    return {
        "count": total_quantity,
        "items": items,
        "cart_total": cart_total,
    }


@router.get("")
def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the authenticated user's cart and total using current catalog prices."""
    return cart_response(db, current_user.id)


@router.post("/items", status_code=201)
def add_cart_item(
    payload: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Add a product variant, increasing its quantity if already in the cart."""
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    _, _, stock = get_variant_price_and_stock(product, payload.variant_id)
    existing = db.scalar(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == payload.product_id,
            CartItem.variant_id == payload.variant_id,
        )
    )
    new_quantity = payload.quantity + (existing.quantity if existing else 0)
    if stock == 0 or new_quantity > stock:
        raise HTTPException(status_code=409, detail="Requested quantity is not available in stock")

    if existing:
        existing.quantity = new_quantity
        item = existing
    else:
        item = CartItem(
            user_id=current_user.id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            quantity=payload.quantity,
        )
        db.add(item)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cart item could not be added") from error
    db.refresh(item)
    return {"message": "Item added to cart", "item_id": item.id, **cart_response(db, current_user.id)}


@router.patch("/items/{item_id}")
def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Set a cart item's quantity after checking current stock."""
    item = db.scalar(
        select(CartItem).where(
            CartItem.id == item_id,
            CartItem.user_id == current_user.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    product = db.get(Product, item.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    _, _, stock = get_variant_price_and_stock(product, item.variant_id)
    if payload.quantity > stock:
        raise HTTPException(status_code=409, detail="Requested quantity is not available in stock")

    item.quantity = payload.quantity
    db.commit()
    return {"message": "Cart quantity updated", **cart_response(db, current_user.id)}


@router.delete("/items/{item_id}")
def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Remove one item belonging to the authenticated user's cart."""
    item = db.scalar(
        select(CartItem).where(
            CartItem.id == item_id,
            CartItem.user_id == current_user.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(item)
    db.commit()
    return {"message": "Item removed from cart", **cart_response(db, current_user.id)}
