import os
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "shopkart-test-secret-key-at-least-32-bytes-long")

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.auth import User
from app.models.cart import CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product


class OrderApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(
            bind=cls.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        app.dependency_overrides[get_db] = self.override_get_db
        self.user_id = self.create_user("buyer@example.com")
        self.token = create_access_token(self.user_id)
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.product_id = self.create_product()

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)

    def override_get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_user(
        self,
        email: str,
        *,
        address: str | None = "123 Market Street",
        pin: str | None = "123456",
    ) -> int:
        with self.SessionLocal() as db:
            user = User(email=email, address=address, pin=pin)
            db.add(user)
            db.commit()
            return user.id

    def create_product(self) -> int:
        with self.SessionLocal() as db:
            product = Product(
                name="Test Product",
                category="Testing",
                reviews=0,
                offers=[],
                variants=[
                    {
                        "variantid": "variant-red",
                        "price": "12.50",
                        "stock": 5,
                        "color": "red",
                    }
                ],
            )
            db.add(product)
            db.commit()
            return product.id

    def add_cart_item(self, *, variant_id: str = "variant-red", quantity: int = 2):
        with self.SessionLocal() as db:
            db.add(
                CartItem(
                    user_id=self.user_id,
                    product_id=self.product_id,
                    variant_id=variant_id,
                    quantity=quantity,
                )
            )
            db.commit()

    def add_order(self, user_id: int, created_at: datetime, order_number: int = 1):
        with self.SessionLocal() as db:
            order = Order(
                user_id=user_id,
                status="placed",
                total_amount=Decimal("12.50"),
                shipping_address="123 Market Street",
                shipping_pin="123456",
                created_at=created_at,
                items=[
                    OrderItem(
                        product_id=self.product_id,
                        product_name=f"Test Product {order_number}",
                        variant_id="variant-red",
                        variant_snapshot={"variantid": "variant-red", "color": "red"},
                        unit_price=Decimal("12.50"),
                        quantity=1,
                        line_total=Decimal("12.50"),
                    )
                ],
            )
            db.add(order)
            db.commit()
            return order.id

    def test_history_requires_valid_access_token(self):
        self.assertEqual(self.client.get("/orders").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            self.client.get(
                "/orders",
                headers={"Authorization": "Bearer invalid"},
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_place_order_snapshots_items_decrements_stock_and_clears_cart(self):
        self.add_cart_item(quantity=2)

        response = self.client.post("/orders", headers=self.headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.text)
        data = response.json()
        self.assertEqual(data["status"], "placed")
        self.assertEqual(data["total_amount"], "25.00")
        self.assertEqual(data["shipping_address"], "123 Market Street")
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["product_name"], "Test Product")
        self.assertEqual(data["items"][0]["variant"]["color"], "red")
        self.assertEqual(data["items"][0]["quantity"], 2)
        self.assertEqual(data["items"][0]["line_total"], "25.00")

        with self.SessionLocal() as db:
            self.assertEqual(db.scalar(select(CartItem.id)), None)
            product = db.get(Product, self.product_id)
            self.assertEqual(product.variants[0]["stock"], 3)
            order = db.get(Order, data["id"])
            self.assertEqual(order.user_id, self.user_id)

    def test_checkout_rejects_empty_cart_and_incomplete_delivery_details(self):
        empty_cart = self.client.post("/orders", headers=self.headers)
        self.assertEqual(empty_cart.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(empty_cart.json()["detail"], "Cannot place an order with an empty cart")

        user_id = self.create_user(
            "incomplete@example.com",
            address=None,
            pin=None,
        )
        token = create_access_token(user_id)
        response = self.client.post(
            "/orders",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery address", response.json()["detail"])

    def test_checkout_rejects_unavailable_variant_and_quantity(self):
        self.add_cart_item(variant_id="missing-variant")
        missing_variant = self.client.post("/orders", headers=self.headers)
        self.assertEqual(missing_variant.status_code, status.HTTP_409_CONFLICT)

        with self.SessionLocal() as db:
            db.query(CartItem).filter(CartItem.user_id == self.user_id).delete()
            db.commit()
        self.add_cart_item(quantity=6)
        unavailable_quantity = self.client.post("/orders", headers=self.headers)
        self.assertEqual(unavailable_quantity.status_code, status.HTTP_409_CONFLICT)

    def test_history_is_user_scoped_and_paginated(self):
        now = datetime.now(timezone.utc)
        self.add_order(self.user_id, now - timedelta(minutes=2), 1)
        self.add_order(self.user_id, now - timedelta(minutes=1), 2)
        other_user_id = self.create_user("other@example.com")
        self.add_order(other_user_id, now, 3)

        first_page = self.client.get(
            "/orders?page=1&pageSize=1",
            headers=self.headers,
        )
        self.assertEqual(first_page.status_code, status.HTTP_200_OK, first_page.text)
        first_data = first_page.json()
        self.assertEqual(first_data["count"], 2)
        self.assertEqual(first_data["page"], 1)
        self.assertEqual(first_data["pageSize"], 1)
        self.assertEqual(first_data["totalPages"], 2)
        self.assertEqual(first_data["orders"][0]["items"][0]["product_name"], "Test Product 2")

        second_page = self.client.get(
            "/orders?page=2&pageSize=1",
            headers=self.headers,
        )
        self.assertEqual(second_page.json()["orders"][0]["items"][0]["product_name"], "Test Product 1")

    def test_history_duration_filters_use_rolling_calendar_windows(self):
        now = datetime.now(timezone.utc)
        self.add_order(self.user_id, now - timedelta(days=45), 1)
        self.add_order(self.user_id, now - timedelta(days=120), 2)
        self.add_order(self.user_id, now - timedelta(days=240), 3)
        self.add_order(self.user_id, now - timedelta(days=430), 4)

        expected_counts = {
            2: 1,
            3: 1,
            6: 2,
            12: 3,
        }
        for duration, expected_count in expected_counts.items():
            with self.subTest(duration=duration):
                response = self.client.get(
                    "/orders",
                    params={"duration": duration},
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
                self.assertEqual(response.json()["count"], expected_count)
                self.assertEqual(response.json()["totalPages"], 1)

    def test_history_year_filter_and_mutually_exclusive_filters(self):
        self.add_order(
            self.user_id,
            datetime(2025, 1, 15, tzinfo=timezone.utc),
            1,
        )
        self.add_order(
            self.user_id,
            datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc),
            2,
        )
        self.add_order(
            self.user_id,
            datetime(2024, 12, 31, tzinfo=timezone.utc),
            3,
        )

        response = self.client.get(
            "/orders?year=2025",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
        self.assertEqual(response.json()["count"], 2)

        conflict = self.client.get(
            "/orders?year=2025&duration=6",
            headers=self.headers,
        )
        self.assertEqual(conflict.status_code, status.HTTP_422_UNPROCESSABLE_CONTENT)

    def test_history_rejects_invalid_pagination_and_duration(self):
        invalid_page = self.client.get(
            "/orders?page=0",
            headers=self.headers,
        )
        invalid_page_size = self.client.get(
            "/orders?pageSize=101",
            headers=self.headers,
        )
        invalid_duration_below_minimum = self.client.get(
            "/orders?duration=0",
            headers=self.headers,
        )
        invalid_duration_above_maximum = self.client.get(
            "/orders?duration=37",
            headers=self.headers,
        )
        self.assertEqual(invalid_page.status_code, status.HTTP_422_UNPROCESSABLE_CONTENT)
        self.assertEqual(invalid_page_size.status_code, status.HTTP_422_UNPROCESSABLE_CONTENT)
        self.assertEqual(invalid_duration_below_minimum.status_code, status.HTTP_422_UNPROCESSABLE_CONTENT)
        self.assertEqual(invalid_duration_above_maximum.status_code, status.HTTP_422_UNPROCESSABLE_CONTENT)


if __name__ == "__main__":
    unittest.main()
