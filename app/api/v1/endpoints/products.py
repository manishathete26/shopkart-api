from fastapi import APIRouter, Depends, HTTPException, Query

from ...deps import get_current_user

router = APIRouter(
    prefix="/products",
    tags=["products"],
    dependencies=[Depends(get_current_user)],
)


def create_variant_with_options(
    product_id: int,
    slug: str,
    options: list[dict[str, str]],
    price: int,
    original_price: int,
    stock: int,
    image_background: str,
    image_query: str,
) -> dict:
    return {
        "id": f"{product_id}-{slug}",
        "productId": product_id,
        "slug": slug,
        "options": options,
        "price": price,
        "originalPrice": original_price,
        "stock": stock,
        "imageBackground": f"#{image_background}",
        "imageQuery": image_query,
    }


_colors = [
    ("Onyx Black", "111111"),
    ("Marble Gray", "b0bec5"),
    ("Cobalt Violet", "b39ddb"),
    ("Amber Yellow", "fff176"),
]
_storage_options = ["128 GB", "256 GB"]


def _slug_part(value: str) -> str:
    return "-".join(value.lower().split())


_product = {
    "id": 2,
    "name": "Samsung Galaxy S24",
    "description": "Premium Samsung smartphone.",
    "category": "Mobiles",
    "subCategory": "Smartphones",
    "brand": "Samsung",
    "rating": 1.7,
    "reviews": 11,
    "offers": ["Bank Offer Flat ₹1,500 off on select cards"],
    "variants": [
        create_variant_with_options(
            2,
            f"{_slug_part(color)}-{_slug_part(storage)}",
            [
                {"type": "color", "label": "Color", "value": color},
                {"type": "storage", "label": "Storage", "value": storage},
            ],
            74999 + color_index * 1000 + storage_index * 5000,
            81999 + color_index * 1000 + storage_index * 5000,
            12 - color_index - storage_index,
            image_background,
            "Galaxy+S24",
        )
        for color_index, (color, image_background) in enumerate(_colors)
        for storage_index, storage in enumerate(_storage_options)
    ],
}

_products = [_product]


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
