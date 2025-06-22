from app.services.ai_service import AIService
from app.models.models import Product, Supplier, InventoryTransaction
from app import db
from datetime import datetime
import re

class ChatbotService:
    def __init__(self):
        self.ai_service = AIService()
        
    def process_message(self, message, user_id=None):
        """
        Process a user message and generate a response
        Returns a dict with response and any additional actions needed
        """
        # First check if this is a confirmation message - this should take priority
        if self._is_confirmation(message):
            return {
                "response": "Thank you for confirming. I'll process the stock update now.",
                "isConfirmation": True
            }              # Check if this is a stock update request
        update_request = self._check_for_stock_update(message)
        if update_request:
            return self._handle_stock_update_request(update_request, user_id)
        
        # Check if this is a request to list low stock products
        if self._is_low_stock_request(message):
            return self._handle_low_stock_request()
            
        # Check if this is a request to list all stock
        if self._is_stock_listing_request(message):
            return self._handle_stock_listing_request()
        
        # Handle general inventory queries
        return self._handle_general_query(message)
    
    def _check_for_stock_update(self, message):
        """Check if the message is a request to update stock"""
        # Pattern to match requests like "add 20 units to product SKU-1234" or "update product SKU-5678 add 10 units"
        add_pattern = r"(?:add|update|increase)\s+(\d+)\s+(?:units?|items?|stock|pieces?)\s+(?:to|for)\s+(?:product\s+)?(?:sku[\s-]*)?([a-zA-Z0-9-]+)"
        
        # Alternative pattern that might have the SKU first
        alt_pattern = r"(?:update|add\s+to)\s+(?:product\s+)?(?:sku[\s-]*)?([a-zA-Z0-9-]+)\s+(?:add|with)\s+(\d+)\s+(?:units?|items?|stock|pieces?)"
        
        # Patterns for decrease/remove operations
        decrease_pattern = r"(?:decrease|reduce|remove|subtract)\s+(\d+)\s+(?:units?|items?|stock|pieces?)\s+(?:from)\s+(?:product\s+)?(?:sku[\s-]*)?([a-zA-Z0-9-]+)"
        
        # Alternative decrease pattern with SKU first
        alt_decrease_pattern = r"(?:update|decrease|reduce|remove\s+from)\s+(?:product\s+)?(?:sku[\s-]*)?([a-zA-Z0-9-]+)\s+(?:decrease|reduce|remove|subtract)\s+(\d+)\s+(?:units?|items?|stock|pieces?)"
        
        # Check first pattern (add)
        match = re.search(add_pattern, message.lower())
        if match:
            quantity = int(match.group(1))
            sku = match.group(2)
            return {"sku": sku, "quantity": quantity, "operation": "add"}
        
        # Check alternative pattern (add)
        match = re.search(alt_pattern, message.lower())
        if match:
            sku = match.group(1)
            quantity = int(match.group(2))
            return {"sku": sku, "quantity": quantity, "operation": "add"}
        
        # Check decrease pattern
        match = re.search(decrease_pattern, message.lower())
        if match:
            quantity = int(match.group(1))
            sku = match.group(2)
            return {"sku": sku, "quantity": quantity, "operation": "remove"}
          # Check alternative decrease pattern
        match = re.search(alt_decrease_pattern, message.lower())
        if match:
            sku = match.group(1)
            quantity = int(match.group(2))
            return {"sku": sku, "quantity": quantity, "operation": "remove"}
            
        return None
    
    def _handle_stock_update_request(self, update_request, user_id):
        """Handle a request to update stock levels"""
        sku = update_request["sku"]
        quantity = update_request["quantity"]
        operation = update_request["operation"]
        
        # Find the product by SKU
        product = Product.query.filter(Product.sku.ilike(f"%{sku}%")).first()
        
        if not product:
            return {
                "response": f"I couldn't find a product with SKU similar to '{sku}'. Please check the SKU and try again."
            }
        
        # Check if we have enough stock for removal operations
        if operation == "remove" and product.quantity_in_stock < quantity:
            return {
                "response": f"I found {product.name} with SKU-{product.sku}, but there are only {product.quantity_in_stock} units in stock. You cannot remove {quantity} units."
            }
        
        # Prepare appropriate message based on operation
        operation_text = "add to" if operation == "add" else "remove from"
        
        # Return with product details for confirmation
        return {
            "response": f"I found {product.name} with SKU-{product.sku}. Current stock level is {product.quantity_in_stock}. Would you like to {operation_text} the stock by {quantity} units?",
            "needsConfirmation": True,
            "product": {
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "current_stock": product.quantity_in_stock,
                "operation": operation,
                "quantity": quantity
            }
        }
        
    def update_stock(self, product_id, quantity, user_id=None):
        """Actually update the stock after confirmation"""
        product = Product.query.get(product_id)
        
        if not product:
            return {"success": False, "message": "Product not found"}
        
        try:
            # Update stock
            original_quantity = product.quantity_in_stock
            product.quantity_in_stock += quantity
              # Create transaction record
            transaction = InventoryTransaction(
                product_id=product.id,
                transaction_type="IN" if quantity > 0 else "OUT",
                quantity=abs(quantity),
                unit_price=product.unit_price,
                total_price=abs(quantity) * product.unit_price,
                notes=f"Stock update via chatbot",
                created_by=user_id if user_id else None
            )
            db.session.add(transaction)
            db.session.commit()
            
            return {
                "success": True,
                "message": f"Successfully updated {product.name} stock from {original_quantity} to {product.quantity_in_stock}."
            }
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Error updating stock: {str(e)}"}
    
    def _is_confirmation(self, message):
        """Check if the message is confirming a previous request"""
        confirmation_words = ["yes", "confirm", "approved", "ok", "okay", "sure", "go ahead", "do it", "y", "yep", "yeah"]
        message_lower = message.lower().strip()
        
        # Check for exact matches first
        if message_lower in confirmation_words:
            return True
            
        # Then check for partial matches
        return any(word in message_lower for word in confirmation_words)
    
    def _is_stock_listing_request(self, message):
        """Check if the message is a request to list all stock"""
        message_lower = message.lower().strip()
        
        # First check if this is a low stock request (to avoid conflicts)
        if self._is_low_stock_request(message_lower):
            return False
            
        listing_patterns = [
            "list all stock", 
            "show all stock",
            "list all products",
            "show all products", 
            "list inventory",
            "show inventory",
            "what products do we have",
            "what items do we have",            "all products",
            "all items",
            "all stock",
            "show me all",
            "list all",
            "all available products",
            "available stock"
        ]
        
        # Check if any of the patterns match the message
        return any(pattern in message_lower for pattern in listing_patterns)
    
    def _is_low_stock_request(self, message):
        """Check if the message is a request to list low stock products"""
        message_lower = message.lower().strip()
        low_stock_patterns = [
            "low stock",
            "stock below",
            "reorder level",
            "need to reorder",
            "running low",
            "stock alert",
            "inventory alert",            "products to reorder",
            "items to reorder",
            "low inventory",
            "inventory running low",
            "list all products with low stock",
            "show products with low stock",
            "which products have low stock",
            "which all have low stock"
        ]
        
        # Check if any of the low stock patterns match the message
        return any(pattern in message_lower for pattern in low_stock_patterns)
        
    def _handle_stock_listing_request(self):
        """Handle a request to list all stock"""
        products = Product.query.order_by(Product.name).all()
        
        if not products:
            return {"response": "There are no products in the inventory."}
        
        # Create HTML formatted response with all products
        response = "<p>Here's the current inventory stock levels:</p>\n<ul>"
        
        for product in products:
            response += f"\n    <li><strong>{product.name}</strong>: SKU: {product.sku}, Stock: {product.quantity_in_stock} units</li>"
        
        response += "\n</ul>"
        
        return {"response": response}
    
    def _handle_low_stock_request(self):
        """Handle a request to list low stock products"""
        low_stock_products = Product.query.filter(Product.quantity_in_stock < Product.reorder_level).order_by(Product.name).all()
        
        if not low_stock_products:
            return {"response": "<p>All products are sufficiently stocked. There are no products with inventory levels below their reorder points.</p>"}
        
        # Create HTML formatted response with low stock products
        response = "<p>Here are the products that need reordering:</p>\n<ul>"
        
        for product in low_stock_products:
            response += f"\n    <li><strong>{product.name}</strong>: SKU: {product.sku}, Stock: {product.quantity_in_stock} units (Reorder level: {product.reorder_level} units)</li>"
        
        response += "\n</ul>"
        
        return {"response": response}
        
    def _handle_general_query(self, message):
        """Handle general inventory-related queries"""
        # Build a system prompt for the AI
        system_prompt = """
        You are an AI assistant for an inventory management system. Answer the user's question about inventory.
        Only respond with information about inventory management, products, stock levels, etc.
        Keep responses concise and helpful. If you don't know an answer, ask for more specific information.
        
        Format your responses with proper HTML for best display:
        - Use <ul> and <li> for lists, not asterisks
        - Use <strong> or <b> for bold text
        - Use <br> for line breaks
        - Ensure each list item is on its own line with proper indentation
        
        When listing products or stock information, ALWAYS use a proper HTML list with <ul> and <li> tags.
        
        Current capabilities:
        - Provide information about product stock levels
        - Answer questions about inventory management
        - Assist with product information
        - Provide supplier information
        - Help with locating products
        
        For stock operations, users can:
        - Add or increase stock: "add 20 units to product SKU-1234" or "update SKU-5678 with 10 units"
        - Remove or decrease stock: "remove 15 units from SKU-1234" or "decrease SKU-5678 by 5 units"
        """
        
        # Get product count for context
        product_count = Product.query.count()
        
        # Add some stats to enrich the prompt with real data
        low_stock_count = Product.query.filter(Product.quantity_in_stock < Product.reorder_level).count()
        
        # Get recent products to help with examples
        recent_products = Product.query.order_by(Product.created_at.desc()).limit(3).all()
        product_examples = "\nCurrent Stock Levels:\n" + "\n".join([
            f"• {p.name.title()}\n"
            f"  SKU: {p.sku}\n"
            f"  Stock: {p.quantity_in_stock} units"
            for p in recent_products
        ])
        
        # Enhance the prompt with real data from database
        enhanced_prompt = f"""
        {system_prompt}
        
        INVENTORY CONTEXT:
        Total products in inventory: {product_count}
        Products with low stock: {low_stock_count}

        {product_examples}
        
        USER QUERY:
        {message}
        """
        
        # Get response from AI service
        response = self.ai_service._generate_content(enhanced_prompt)
        
        return {"response": response}
