#!/usr/bin/env python3
"""
Unit tests for E-Commerce Cloud Storage System
Author: Gabriel Demetrios Lafis
"""

import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

from app import (
    Product, AzureKeyVaultManager, DatabaseManager, 
    BlobStorageManager, ECommerceSystem
)

class TestProduct(unittest.TestCase):
    """Test cases for Product data model"""
    
    def test_product_creation(self):
        """Test product creation with default values"""
        product = Product()
        self.assertIsNone(product.product_id)
        self.assertEqual(product.name, "")
        self.assertEqual(product.description, "")
        self.assertEqual(product.price, 0.0)
        self.assertEqual(product.image_url, "")
        self.assertIsNone(product.created_at)
    
    def test_product_creation_with_values(self):
        """Test product creation with specific values"""
        now = datetime.now()
        product = Product(
            product_id=1,
            name="Test Product",
            description="A test product",
            price=99.99,
            image_url="https://example.com/image.jpg",
            created_at=now
        )
        
        self.assertEqual(product.product_id, 1)
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.description, "A test product")
        self.assertEqual(product.price, 99.99)
        self.assertEqual(product.image_url, "https://example.com/image.jpg")
        self.assertEqual(product.created_at, now)

class TestAzureKeyVaultManager(unittest.TestCase):
    """Test cases for Azure Key Vault Manager"""
    
    @patch('app.SecretClient')
    @patch('app.DefaultAzureCredential')
    def test_key_vault_initialization(self, mock_credential, mock_client):
        """Test Key Vault manager initialization"""
        vault_url = "https://test-vault.vault.azure.net/"
        manager = AzureKeyVaultManager(vault_url)
        
        self.assertEqual(manager.vault_url, vault_url)
        mock_credential.assert_called_once()
        mock_client.assert_called_once()
    
    @patch('app.SecretClient')
    @patch('app.DefaultAzureCredential')
    def test_get_secret_success(self, mock_credential, mock_client):
        """Test successful secret retrieval"""
        # Mock secret object
        mock_secret = MagicMock()
        mock_secret.value = "test-secret-value"
        
        # Mock client instance
        mock_client_instance = MagicMock()
        mock_client_instance.get_secret.return_value = mock_secret
        mock_client.return_value = mock_client_instance
        
        vault_url = "https://test-vault.vault.azure.net/"
        manager = AzureKeyVaultManager(vault_url)
        
        result = manager.get_secret("test-secret")
        self.assertEqual(result, "test-secret-value")
        mock_client_instance.get_secret.assert_called_once_with("test-secret")
    
    @patch('app.SecretClient')
    @patch('app.DefaultAzureCredential')
    def test_get_secret_failure(self, mock_credential, mock_client):
        """Test secret retrieval failure"""
        # Mock client instance to raise exception
        mock_client_instance = MagicMock()
        mock_client_instance.get_secret.side_effect = Exception("Secret not found")
        mock_client.return_value = mock_client_instance
        
        vault_url = "https://test-vault.vault.azure.net/"
        manager = AzureKeyVaultManager(vault_url)
        
        with self.assertRaises(Exception):
            manager.get_secret("nonexistent-secret")

class TestDatabaseManager(unittest.TestCase):
    """Test cases for Database Manager"""
    
    @patch('app.pyodbc.connect')
    def test_database_initialization(self, mock_connect):
        """Test database initialization"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        connection_string = "test-connection-string"
        db_manager = DatabaseManager(connection_string)
        
        self.assertEqual(db_manager.connection_string, connection_string)
        mock_connect.assert_called_with(connection_string)
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
    
    @patch('app.pyodbc.connect')
    def test_add_product(self, mock_connect):
        """Test adding a product"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [123]  # Mock product ID
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        db_manager = DatabaseManager("test-connection-string")
        product = Product(name="Test Product", description="Test", price=99.99)
        
        product_id = db_manager.add_product(product)
        
        self.assertEqual(product_id, 123)
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
    
    @patch('app.pyodbc.connect')
    def test_get_product_found(self, mock_connect):
        """Test getting an existing product"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [
            1, "Test Product", "Test Description", 99.99, 
            "https://example.com/image.jpg", datetime.now()
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        db_manager = DatabaseManager("test-connection-string")
        product = db_manager.get_product(1)
        
        self.assertIsNotNone(product)
        self.assertEqual(product.product_id, 1)
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price, 99.99)
    
    @patch('app.pyodbc.connect')
    def test_get_product_not_found(self, mock_connect):
        """Test getting a non-existent product"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        db_manager = DatabaseManager("test-connection-string")
        product = db_manager.get_product(999)
        
        self.assertIsNone(product)
    
    @patch('app.pyodbc.connect')
    def test_list_products(self, mock_connect):
        """Test listing products"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            [1, "Product 1", "Description 1", 99.99, "url1", datetime.now()],
            [2, "Product 2", "Description 2", 149.99, "url2", datetime.now()]
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        db_manager = DatabaseManager("test-connection-string")
        products = db_manager.list_products()
        
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].name, "Product 1")
        self.assertEqual(products[1].name, "Product 2")
    
    @patch('app.pyodbc.connect')
    def test_update_product(self, mock_connect):
        """Test updating a product"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1  # One row affected
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        db_manager = DatabaseManager("test-connection-string")
        product = Product(
            product_id=1, name="Updated Product", 
            description="Updated", price=199.99
        )
        
        result = db_manager.update_product(product)
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
    
    @patch('app.pyodbc.connect')
    def test_delete_product(self, mock_connect):
        """Test deleting a product"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1  # One row affected
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        db_manager = DatabaseManager("test-connection-string")
        result = db_manager.delete_product(1)
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

class TestBlobStorageManager(unittest.TestCase):
    """Test cases for Blob Storage Manager"""
    
    @patch('app.BlobServiceClient.from_connection_string')
    def test_blob_storage_initialization(self, mock_blob_client):
        """Test blob storage initialization"""
        mock_container_client = MagicMock()
        mock_container_client.exists.return_value = True
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client
        
        connection_string = "test-connection-string"
        blob_manager = BlobStorageManager(connection_string)
        
        self.assertEqual(blob_manager.connection_string, connection_string)
        self.assertEqual(blob_manager.container_name, "product-images")
    
    @patch('app.BlobServiceClient.from_connection_string')
    @patch('builtins.open', new_callable=mock_open, read_data=b"fake image data")
    @patch('os.path.exists')
    def test_upload_image(self, mock_exists, mock_file, mock_blob_client):
        """Test image upload"""
        mock_exists.return_value = True
        mock_blob_instance = MagicMock()
        mock_blob_instance.url = "https://example.com/image.jpg"
        mock_blob_client.return_value.get_blob_client.return_value = mock_blob_instance
        
        # Mock container client
        mock_container_client = MagicMock()
        mock_container_client.exists.return_value = True
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client
        
        blob_manager = BlobStorageManager("test-connection-string")
        result = blob_manager.upload_image(1, "/fake/path/image.jpg")
        
        self.assertEqual(result, "https://example.com/image.jpg")
        mock_blob_instance.upload_blob.assert_called_once()
    
    @patch('app.BlobServiceClient.from_connection_string')
    def test_delete_image(self, mock_blob_client):
        """Test image deletion"""
        mock_blob_instance = MagicMock()
        mock_blob_client.return_value.get_blob_client.return_value = mock_blob_instance
        
        # Mock container client
        mock_container_client = MagicMock()
        mock_container_client.exists.return_value = True
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client
        
        blob_manager = BlobStorageManager("test-connection-string")
        result = blob_manager.delete_image("https://example.com/container/image.jpg")
        
        self.assertTrue(result)
        mock_blob_instance.delete_blob.assert_called_once()

class TestECommerceSystem(unittest.TestCase):
    """Test cases for E-Commerce System"""
    
    @patch.dict(os.environ, {'KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'})
    @patch('app.AzureKeyVaultManager')
    @patch('app.DatabaseManager')
    @patch('app.BlobStorageManager')
    def test_ecommerce_system_initialization(self, mock_blob, mock_db, mock_kv):
        """Test e-commerce system initialization"""
        # Mock Key Vault manager
        mock_kv_instance = MagicMock()
        mock_kv_instance.get_secret.side_effect = [
            "sql-connection-string",
            "blob-connection-string"
        ]
        mock_kv.return_value = mock_kv_instance
        
        ecommerce = ECommerceSystem()
        
        self.assertIsNotNone(ecommerce.key_vault)
        self.assertIsNotNone(ecommerce.db_manager)
        self.assertIsNotNone(ecommerce.blob_manager)
    
    def test_ecommerce_system_missing_env_var(self):
        """Test e-commerce system with missing environment variable"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                ECommerceSystem()
    
    @patch.dict(os.environ, {'KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'})
    @patch('app.AzureKeyVaultManager')
    @patch('app.DatabaseManager')
    @patch('app.BlobStorageManager')
    @patch('os.path.exists')
    def test_add_product_with_image(self, mock_exists, mock_blob, mock_db, mock_kv):
        """Test adding a product with image"""
        mock_exists.return_value = True
        
        # Mock Key Vault
        mock_kv_instance = MagicMock()
        mock_kv_instance.get_secret.side_effect = [
            "sql-connection-string",
            "blob-connection-string"
        ]
        mock_kv.return_value = mock_kv_instance
        
        # Mock Database Manager
        mock_db_instance = MagicMock()
        mock_db_instance.add_product.return_value = 123
        mock_db.return_value = mock_db_instance
        
        # Mock Blob Manager
        mock_blob_instance = MagicMock()
        mock_blob_instance.upload_image.return_value = "https://example.com/image.jpg"
        mock_blob.return_value = mock_blob_instance
        
        ecommerce = ECommerceSystem()
        product_id = ecommerce.add_product(
            "Test Product", "Description", 99.99, "/fake/image.jpg"
        )
        
        self.assertEqual(product_id, 123)
        mock_db_instance.add_product.assert_called()
        mock_blob_instance.upload_image.assert_called_with(123, "/fake/image.jpg")
        mock_db_instance.update_product.assert_called()
    
    @patch.dict(os.environ, {'KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'})
    @patch('app.AzureKeyVaultManager')
    @patch('app.DatabaseManager')
    @patch('app.BlobStorageManager')
    def test_get_product(self, mock_blob, mock_db, mock_kv):
        """Test getting a product"""
        # Mock Key Vault
        mock_kv_instance = MagicMock()
        mock_kv_instance.get_secret.side_effect = [
            "sql-connection-string",
            "blob-connection-string"
        ]
        mock_kv.return_value = mock_kv_instance
        
        # Mock Database Manager
        mock_product = Product(
            product_id=1, name="Test Product", description="Test", 
            price=99.99, created_at=datetime.now()
        )
        mock_db_instance = MagicMock()
        mock_db_instance.get_product.return_value = mock_product
        mock_db.return_value = mock_db_instance
        
        ecommerce = ECommerceSystem()
        result = ecommerce.get_product(1)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['ProductId'], 1)
        self.assertEqual(result['Name'], "Test Product")
        self.assertEqual(result['Price'], 99.99)

class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    @patch.dict(os.environ, {'KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'})
    @patch('app.AzureKeyVaultManager')
    @patch('app.pyodbc.connect')
    @patch('app.BlobServiceClient.from_connection_string')
    def test_full_product_lifecycle(self, mock_blob_client, mock_db_connect, mock_kv):
        """Test complete product lifecycle"""
        # Mock Key Vault
        mock_kv_instance = MagicMock()
        mock_kv_instance.get_secret.side_effect = [
            "sql-connection-string",
            "blob-connection-string"
        ]
        mock_kv.return_value = mock_kv_instance
        
        # Mock database operations
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [1]  # Product ID for add
        mock_cursor.rowcount = 1  # For update/delete operations
        mock_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value.__enter__.return_value = mock_conn
        
        # Mock blob storage
        mock_container_client = MagicMock()
        mock_container_client.exists.return_value = True
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client
        
        # Test the system
        ecommerce = ECommerceSystem()
        
        # Add product
        product_id = ecommerce.add_product("Test Product", "Description", 99.99)
        self.assertEqual(product_id, 1)
        
        # Verify database calls were made
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestProduct))
    test_suite.addTest(unittest.makeSuite(TestAzureKeyVaultManager))
    test_suite.addTest(unittest.makeSuite(TestDatabaseManager))
    test_suite.addTest(unittest.makeSuite(TestBlobStorageManager))
    test_suite.addTest(unittest.makeSuite(TestECommerceSystem))
    test_suite.addTest(unittest.makeSuite(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
