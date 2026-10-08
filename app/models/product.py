from sqlalchemy import Float, Integer, JSON, String, Text
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
    variants: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    badge: Mapped[str | None] = mapped_column(String(120))

    wishlist_items: Mapped[list["WishlistItem"]] = relationship(
        back_populates="product", passive_deletes=True
    )
