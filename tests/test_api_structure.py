import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["MAIL_USERNAME"] = ""
os.environ["MAIL_PASSWORD"] = ""
os.environ["MAIL_FROM"] = ""

import unittest

from fastapi.testclient import TestClient

from app.main import app


EXPECTED_AUTH_OPERATIONS = (
    ("post", "/auth/send-otp", "send_otp_auth_send_otp_post"),
    ("post", "/auth/verify-otp", "verify_otp_auth_verify_otp_post"),
    ("post", "/auth/create-profile", "create_profile_auth_create_profile_post"),
    ("post", "/auth/refresh", "refresh_token_auth_refresh_post"),
    ("post", "/auth/logout", "logout_auth_logout_post"),
    ("get", "/auth/me", "read_current_user_auth_me_get"),
)


class AuthStructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_app_metadata(self):
        self.assertEqual(app.title, "ShopKart Authentication API")
        self.assertEqual(app.version, "1.0.0")

    def test_openapi_auth_operations(self):
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        document = response.json()
        self.assertEqual(document["info"]["title"], "ShopKart Authentication API")
        self.assertEqual(document["info"]["version"], "1.0.0")

        paths = document["paths"]
        self.assertEqual(
            {path for _, path, _ in EXPECTED_AUTH_OPERATIONS},
            {path for path in paths if path.startswith("/auth/")},
        )
        for method, path, operation_id in EXPECTED_AUTH_OPERATIONS:
            with self.subTest(path=path):
                self.assertIn(method, paths[path])
                self.assertEqual(paths[path][method]["operationId"], operation_id)

    def test_safe_auth_error_paths(self):
        cases = (
            ("GET", "/auth/me", None, None, 401, "Not authenticated"),
            (
                "GET",
                "/auth/me",
                None,
                {"Authorization": "Bearer invalid"},
                401,
                "Invalid access token",
            ),
            ("POST", "/auth/verify-otp", {}, None, 422, None),
            (
                "POST",
                "/auth/refresh",
                {"refresh_token": "invalid"},
                None,
                401,
                "Invalid refresh token",
            ),
            (
                "POST",
                "/auth/logout",
                {"refresh_token": "invalid"},
                None,
                400,
                "Invalid refresh token",
            ),
            (
                "POST",
                "/auth/send-otp",
                {"email": "user@example.com"},
                None,
                500,
                "Email service is not configured.",
            ),
        )

        for method, path, payload, headers, expected_status, expected_detail in cases:
            with self.subTest(method=method, path=path):
                response = self.client.request(method, path, json=payload, headers=headers)

                self.assertEqual(response.status_code, expected_status)
                if expected_detail is not None:
                    self.assertEqual(response.json()["detail"], expected_detail)


if __name__ == "__main__":
    unittest.main()
