import unittest
from database.database import (
    init_database, add_product, get_all_products,
    delete_product, authenticate_user
)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        init_database()

    def test_authentication(self):
        self.assertTrue(authenticate_user("admin", "admin123"))
        self.assertFalse(authenticate_user("wrong", "wrong"))

    def test_add_and_get_product(self):
        add_product("TEST123", "Test Product", "Test", "Brand", 10.0, 5, "Supplier", "2025-12-31")
        products = get_all_products()
        found = any(p[1] == "TEST123" for p in products)
        self.assertTrue(found)
        delete_product("TEST123")


if __name__ == "__main__":
    unittest.main()