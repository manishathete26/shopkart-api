from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    sub_category: Mapped[str | None] = mapped_column("subCategory", String(120))
    brand: Mapped[str | None] = mapped_column(String(120), index=True)
    rating: Mapped[float | None] = mapped_column(Float)
    reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    offers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    badge: Mapped[str | None] = mapped_column(String(120))

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductVariant.variantid",
    )
    wishlist_items: Mapped[list["WishlistItem"]] = relationship(
        back_populates="product", passive_deletes=True
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    variantid: Mapped[str] = mapped_column(String(255), primary_key=True)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The catalog JSON has a productId per variant as well as its parentId.
    variant_product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    original_price: Mapped[int] = mapped_column("originalPrice", Integer, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    images: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    product: Mapped[Product] = relationship(back_populates="variants")
