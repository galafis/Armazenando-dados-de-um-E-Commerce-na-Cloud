#!/usr/bin/env python3
"""
E-Commerce Cloud Storage System
Secure data storage solution using Azure SQL Database and Blob Storage
Author: Gabriel Demetrios Lafis
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pathlib import Path

import pyodbc
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Product:
    """Product data model"""
    product_id: Optional[int] = None
    name: str = ""
    description: str = ""
    price: float = 0.0
    image_url: str = ""
    created_at: Optional[datetime] = None

class AzureKeyVaultManager:
    """Manages Azure Key Vault operations for secure credential storage"""
    
    def __init__(self, vault_url: str):
        self.vault_url = vault_url
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=self.credential)
    
    def get_secret(self, secret_name: str) -> str:
        """Retrieve a secret from Azure Key Vault"""
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
            raise

class DatabaseManager:
    """Manages Azure SQL Database operations"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                # Create Products table if it doesn't exist
                create_table_sql = """
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Products' AND xtype='U')
                CREATE TABLE Products (
                    ProductId INT PRIMARY KEY IDENTITY(1,1),
                    Name NVARCHAR(100) NOT NULL,
                    Description NVARCHAR(MAX),
                    Price DECIMAL(18,2) NOT NULL,
                    ImageUrl NVARCHAR(255),
                    CreatedAt DATETIME DEFAULT GETDATE()
                );
                """
                cursor.execute(create_table_sql)
                
                # Create indexes for better performance
                index_sql = """
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Products_Name')
                CREATE INDEX IX_Products_Name ON Products(Name);
                
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Products_Price')
                CREATE INDEX IX_Products_Price ON Products(Price);
                """
                cursor.execute(index_sql)
                
                conn.commit()
                logger.info("Database schema initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
    
    def add_product(self, product: Product) -> int:
        """Add a new product to the database"""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                insert_sql = """
                INSERT INTO Products (Name, Description, Price, ImageUrl)
                OUTPUT INSERTED.ProductId
                VALUES (?, ?, ?, ?)
                """
                
                cursor.execute(insert_sql, product.name, product.description, 
                             product.price, product.image_url)
                
                product_id = cursor.fetchone()[0]
                conn.commit()
                
                logger.info(f"Product added successfully with ID: {product_id}")
                return product_id
                
        except Exception as e:
            logger.error(f"Error adding product: {str(e)}")
            raise
    
    def get_product(self, product_id: int) -> Optional[Product]:
        """Retrieve a product by ID"""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                select_sql = """
                SELECT ProductId, Name, Description, Price, ImageUrl, CreatedAt
                FROM Products
                WHERE ProductId = ?
                """
                
                cursor.execute(select_sql, product_id)
                row = cursor.fetchone()
                
                if row:
                    return Product(
                        product_id=row[0],
                        name=row[1],
                        description=row[2],
                        price=float(row[3]),
                        image_url=row[4],
                        created_at=row[5]
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving product {product_id}: {str(e)}")
            raise
    
    def list_products(self, limit: int = 50) -> List[Product]:
        """List all products with optional limit"""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                select_sql = f"""
                SELECT TOP {limit} ProductId, Name, Description, Price, ImageUrl, CreatedAt
                FROM Products
                ORDER BY CreatedAt DESC
                """
                
                cursor.execute(select_sql)
                rows = cursor.fetchall()
                
                products = []
                for row in rows:
                    products.append(Product(
                        product_id=row[0],
                        name=row[1],
                        description=row[2],
                        price=float(row[3]),
                        image_url=row[4],
                        created_at=row[5]
                    ))
                
                return products
                
        except Exception as e:
            logger.error(f"Error listing products: {str(e)}")
            raise
    
    def update_product(self, product: Product) -> bool:
        """Update an existing product"""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                update_sql = """
                UPDATE Products
                SET Name = ?, Description = ?, Price = ?, ImageUrl = ?
                WHERE ProductId = ?
                """
                
                cursor.execute(update_sql, product.name, product.description,
                             product.price, product.image_url, product.product_id)
                
                rows_affected = cursor.rowcount
                conn.commit()
                
                if rows_affected > 0:
                    logger.info(f"Product {product.product_id} updated successfully")
                    return True
                else:
                    logger.warning(f"Product {product.product_id} not found for update")
                    return False
                
        except Exception as e:
            logger.error(f"Error updating product {product.product_id}: {str(e)}")
            raise
    
    def delete_product(self, product_id: int) -> bool:
        """Delete a product by ID"""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                delete_sql = "DELETE FROM Products WHERE ProductId = ?"
                cursor.execute(delete_sql, product_id)
                
                rows_affected = cursor.rowcount
                conn.commit()
                
                if rows_affected > 0:
                    logger.info(f"Product {product_id} deleted successfully")
                    return True
                else:
                    logger.warning(f"Product {product_id} not found for deletion")
                    return False
                
        except Exception as e:
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            raise

class BlobStorageManager:
    """Manages Azure Blob Storage operations for product images"""
    
    def __init__(self, connection_string: str, container_name: str = "product-images"):
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.init_container()
    
    def init_container(self):
        """Initialize blob container"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            # Create container if it doesn't exist
            if not container_client.exists():
                container_client.create_container(public_access='blob')
                logger.info(f"Container '{self.container_name}' created successfully")
            else:
                logger.info(f"Container '{self.container_name}' already exists")
                
        except Exception as e:
            logger.error(f"Error initializing container: {str(e)}")
            raise
    
    def upload_image(self, product_id: int, image_path: str, content_type: str = "image/jpeg") -> str:
        """Upload product image to blob storage"""
        try:
            # Generate unique blob name
            file_extension = Path(image_path).suffix
            blob_name = f"product-{product_id}-{uuid.uuid4()}{file_extension}"
            
            # Upload file
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            with open(image_path, 'rb') as data:
                blob_client.upload_blob(
                    data, 
                    content_settings={'content_type': content_type},
                    overwrite=True
                )
            
            # Return the public URL
            image_url = blob_client.url
            logger.info(f"Image uploaded successfully: {image_url}")
            return image_url
            
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
            raise
    
    def delete_image(self, image_url: str) -> bool:
        """Delete image from blob storage"""
        try:
            # Extract blob name from URL
            blob_name = image_url.split('/')[-1]
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info(f"Image deleted successfully: {blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting image: {str(e)}")
            return False

class ECommerceSystem:
    """Main e-commerce system class"""
    
    def __init__(self):
        self.key_vault_url = os.getenv('KEY_VAULT_URL')
        
        if not self.key_vault_url:
            raise ValueError("KEY_VAULT_URL environment variable is required")
        
        # Initialize Azure Key Vault
        self.key_vault = AzureKeyVaultManager(self.key_vault_url)
        
        # Get connection strings from Key Vault
        sql_connection_string = self.key_vault.get_secret('sql-connection-string')
        blob_connection_string = self.key_vault.get_secret('blob-connection-string')
        
        # Initialize managers
        self.db_manager = DatabaseManager(sql_connection_string)
        self.blob_manager = BlobStorageManager(blob_connection_string)
        
        logger.info("E-Commerce system initialized successfully")
    
    def add_product(self, name: str, description: str, price: float, image_path: Optional[str] = None) -> int:
        """Add a new product with optional image"""
        try:
            # Create product object
            product = Product(name=name, description=description, price=price)
            
            # Add product to database first
            product_id = self.db_manager.add_product(product)
            
            # Upload image if provided
            if image_path and os.path.exists(image_path):
                image_url = self.blob_manager.upload_image(product_id, image_path)
                
                # Update product with image URL
                product.product_id = product_id
                product.image_url = image_url
                self.db_manager.update_product(product)
            
            return product_id
            
        except Exception as e:
            logger.error(f"Error adding product: {str(e)}")
            raise
    
    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get product information"""
        try:
            product = self.db_manager.get_product(product_id)
            
            if product:
                return {
                    'ProductId': product.product_id,
                    'Name': product.name,
                    'Description': product.description,
                    'Price': product.price,
                    'ImageUrl': product.image_url,
                    'CreatedAt': product.created_at.isoformat() if product.created_at else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting product: {str(e)}")
            raise
    
    def list_products(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all products"""
        try:
            products = self.db_manager.list_products(limit)
            
            return [
                {
                    'ProductId': p.product_id,
                    'Name': p.name,
                    'Description': p.description,
                    'Price': p.price,
                    'ImageUrl': p.image_url,
                    'CreatedAt': p.created_at.isoformat() if p.created_at else None
                }
                for p in products
            ]
            
        except Exception as e:
            logger.error(f"Error listing products: {str(e)}")
            raise

# Example usage and testing functions
def main():
    """Main function for testing the system"""
    try:
        # Initialize the e-commerce system
        ecommerce = ECommerceSystem()
        
        # Example: Add a product
        print("Adding a sample product...")
        product_id = ecommerce.add_product(
            name="Sample Laptop",
            description="A high-performance laptop for professionals",
            price=1299.99
        )
        print(f"Product added with ID: {product_id}")
        
        # Example: Get the product
        print(f"Retrieving product {product_id}...")
        product = ecommerce.get_product(product_id)
        if product:
            print(f"Product found: {product['Name']} - ${product['Price']}")
        else:
            print("Product not found")
        
        # Example: List all products
        print("Listing all products...")
        products = ecommerce.list_products()
        print(f"Found {len(products)} products")
        
        for p in products:
            print(f"- {p['Name']}: ${p['Price']}")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    main()
