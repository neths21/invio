"""
Inventory service for the Discord bot.
This module provides integration with the inventory management system.
"""
import os
import sys
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger("discord-bot.inventory")

# Add the parent directory to the Python path to import app modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import app services and models
try:
    from app.services.chatbot_service import ChatbotService
    from app.models.models import Product, InventoryTransaction
    
    # Initialize the chatbot service
    chatbot_service = ChatbotService()
    logger.info("Successfully loaded inventory services and models")
except ImportError as e:
    logger.error(f"Error importing inventory services: {e}")
    chatbot_service = None


class InventoryService:
    """Service for interacting with the inventory management system."""
    
    def __init__(self):
        """Initialize the inventory service."""
        self.chatbot_service = chatbot_service
    
    def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get a product by its SKU.
        
        Args:
            sku: The product SKU to look up
            
        Returns:
            A dictionary with product information or None if not found
        """
        if not chatbot_service:
            logger.error("Chatbot service not available")
            return None
            
        try:
            # Use the existing system's database models
            from app import db
            product = Product.query.filter(Product.sku.ilike(f"%{sku}%")).first()
            
            if not product:
                return None
                
            return {
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "description": product.description,
                "quantity_in_stock": product.quantity_in_stock,
                "unit_price": float(product.unit_price) if product.unit_price else 0,
                "reorder_level": product.reorder_level
            }
        except Exception as e:
            logger.error(f"Error getting product by SKU: {e}")
            return None
    
    def get_low_stock_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get a list of products with stock levels below their reorder point.
        
        Args:
            limit: Maximum number of products to return
            
        Returns:
            A list of product dictionaries
        """
        if not chatbot_service:
            logger.error("Chatbot service not available")
            return []
            
        try:
            # Use the existing system's database models
            from app import db
            products = Product.query.filter(
                Product.quantity_in_stock < Product.reorder_level
            ).limit(limit).all()
            
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "quantity_in_stock": p.quantity_in_stock,
                    "reorder_level": p.reorder_level,
                    "shortage": p.reorder_level - p.quantity_in_stock
                }
                for p in products
            ]
        except Exception as e:
            logger.error(f"Error getting low stock products: {e}")
            return []
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the inventory status.
        
        Returns:
            A dictionary with inventory summary information
        """
        if not chatbot_service:
            logger.error("Chatbot service not available")
            return {
                "total_products": 0,
                "low_stock_count": 0,
                "products": []
            }
            
        try:
            # Use the existing system's database models
            from app import db
            
            # Get counts
            total_products = Product.query.count()
            low_stock_count = Product.query.filter(
                Product.quantity_in_stock < Product.reorder_level
            ).count()
            
            # Get some recent products
            recent_products = Product.query.order_by(
                Product.created_at.desc()
            ).limit(5).all()
            
            return {
                "total_products": total_products,
                "low_stock_count": low_stock_count,
                "products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "sku": p.sku,
                        "quantity_in_stock": p.quantity_in_stock,
                        "reorder_level": p.reorder_level
                    }
                    for p in recent_products
                ]
            }
        except Exception as e:
            logger.error(f"Error getting inventory summary: {e}")
            return {
                "total_products": 0,
                "low_stock_count": 0,
                "products": []
            }
    
    def update_stock(self, sku: str, quantity: int, user_id: str) -> Dict[str, Any]:
        """
        Update stock levels for a product.
        
        Args:
            sku: The product SKU
            quantity: The quantity to add (positive) or remove (negative)
            user_id: The ID of the user making the change
            
        Returns:
            A dictionary with the result of the operation
        """
        if not chatbot_service:
            logger.error("Chatbot service not available")
            return {
                "success": False,
                "message": "Inventory service not available"
            }
            
        try:
            # First get the product by SKU
            product = Product.query.filter(Product.sku.ilike(f"%{sku}%")).first()
            
            if not product:
                return {
                    "success": False,
                    "message": f"Product with SKU similar to '{sku}' not found"
                }
            
            # Check if we have enough stock for removal
            if quantity < 0 and product.quantity_in_stock < abs(quantity):
                return {
                    "success": False,
                    "message": f"Not enough stock. Current stock: {product.quantity_in_stock}, Requested removal: {abs(quantity)}"
                }
            
            # Use the existing chatbot service to update stock
            result = chatbot_service.update_stock(
                product.id,
                quantity,
                user_id
            )
            
            return result
        except Exception as e:
            logger.error(f"Error updating stock: {e}")
            return {
                "success": False,
                "message": f"Error updating stock: {str(e)}"
            }
    
    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for products by name or SKU.
        
        Args:
            query: The search query
            limit: Maximum number of products to return
            
        Returns:
            A list of matching product dictionaries
        """
        if not chatbot_service:
            logger.error("Chatbot service not available")
            return []
            
        try:
            # Use the existing system's database models
            from app import db
            products = Product.query.filter(
                (Product.name.ilike(f"%{query}%")) | 
                (Product.sku.ilike(f"%{query}%")) |
                (Product.description.ilike(f"%{query}%"))
            ).limit(limit).all()
            
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "description": p.description,
                    "quantity_in_stock": p.quantity_in_stock,
                    "unit_price": float(p.unit_price) if p.unit_price else 0
                }
                for p in products
            ]
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []
