from fastapi import APIRouter

from .endpoints.auth import router as auth_router
from .endpoints.cart import router as cart_router
from .endpoints.catalog import router as catalog_router
from .endpoints.products import router as products_router
from .endpoints.wishlist import router as wishlist_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(cart_router)
api_router.include_router(catalog_router)
api_router.include_router(products_router)
api_router.include_router(wishlist_router)
