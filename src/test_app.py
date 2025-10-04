import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app import ECommerceSystem, Product, DatabaseManager, BlobStorageManager

class TestECommerceSystem(unittest.TestCase):

    def setUp(self):
        # Initialize ECommerceSystem in mock mode for testing
        self.system = ECommerceSystem(mock_mode=True)

    def test_add_product(self):
        print("\n--- Running test_add_product ---")
        product_id = self.system.add_product("Test Product", "Description", 10.0, "image.jpg")
        self.assertIsNotNone(product_id)
        self.assertEqual(product_id, 1) # In mock mode, it always returns 1
        print(f"Product added with ID: {product_id}")

    def test_get_product(self):
        print("\n--- Running test_get_product ---")
        # Add a product first (mocked)
        self.system.add_product("Test Product", "Description", 10.0, "image.jpg")
        
        product = self.system.get_product(1)
        self.assertIsNotNone(product)
        self.assertEqual(product.product_id, 1)
        self.assertEqual(product.name, "Sample Laptop (Mock)")
        print(f"Product retrieved: {product.name}")

    def test_list_products(self):
        print("\n--- Running test_list_products ---")
        products = self.system.list_products()
        self.assertIsNotNone(products)
        self.assertEqual(len(products), 2) # Mock mode returns 2 sample products
        self.assertEqual(products[0].name, "Sample Laptop (Mock)")
        self.assertEqual(products[1].name, "Sample Smartphone (Mock)")
        print(f"Products listed: {[p.name for p in products]}")

    def test_update_product(self):
        print("\n--- Running test_update_product ---")
        # Add a product first (mocked)
        self.system.add_product("Test Product", "Description", 10.0, "image.jpg")

        updated_product = Product(
            product_id=1,
            name="Updated Product (Mock)",
            description="Updated Description (Mock)",
            price=15.0,
            image_url="updated_image.jpg",
            created_at=datetime.now()
        )
        result = self.system.update_product(updated_product)
        self.assertTrue(result)
        print(f"Product updated: {updated_product.name}")

    def test_delete_product(self):
        print("\n--- Running test_delete_product ---")
        # Add a product first (mocked)
        self.system.add_product("Test Product", "Description", 10.0, "image.jpg")

        result = self.system.delete_product(1)
        self.assertTrue(result)
        print(f"Product deleted with ID: 1")

    def test_upload_and_delete_image(self):
        print("\n--- Running test_upload_and_delete_image ---")
        # In mock mode, these operations return mock URLs and True
        mock_image_path = "/tmp/test_image.jpg"
        with open(mock_image_path, "w") as f:
            f.write("mock image content")

        image_url = self.system.upload_image(1, mock_image_path)
        self.assertIsNotNone(image_url)
        self.assertTrue("mockimage.com" in image_url)
        print(f"Image uploaded to: {image_url}")

        result = self.system.delete_image(image_url)
        self.assertTrue(result)
        print(f"Image deleted: {image_url}")

if __name__ == '__main__':
    unittest.main()
