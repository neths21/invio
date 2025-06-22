import os
import requests
import json
import logging
import datetime
import re  # Added for markdown conversion
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Gemini API key from environment variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class AIService:
    def __init__(self):
        # New Gemini 2.0 API base URL
        self.api_base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        self.api_key = GEMINI_API_KEY
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY environment variable not set. AI service functionality will be limited.")
    
    def _generate_content(self, prompt):
        """Make API call to Gemini 2.0 Flash model"""
        url = f"{self.api_base_url}?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }                    ]
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            
            response_data = response.json()
            logger.debug(f"Gemini API response: {response_data}")
            
            # Extract text from the response based on the Gemini 2.0 response format
            if 'candidates' in response_data and len(response_data['candidates']) > 0:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    text_parts = [part.get('text', '') for part in parts if 'text' in part]
                    return ''.join(text_parts)
            
            # Fallback if the expected structure is not found
            logger.warning("Unable to extract content from Gemini API response")
            return "Unable to generate content. Please try again later."
            
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            if response.status_code == 404:
                logger.error("404 error: Check API endpoint URL is correct")
            return f"Error generating content: {str(http_err)}"
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return f"Error generating content: {str(e)}"
    
    def generate_low_stock_notification(self, product, supplier):
        """Generate a notification for low stock products"""
        if not self.api_key:
            return f"Low stock alert for {product.name}. Current stock: {product.quantity_in_stock}. Please reorder {product.reorder_quantity} units from {supplier.name}."
        
        prompt = f"""
        Product '{product.name}' (SKU: {product.sku}) is running low on stock.
        Current quantity: {product.quantity_in_stock}
        Reorder level: {product.reorder_level}
        Supplier: {supplier.name}
        
        Please generate a concise, human-readable notification about this low stock situation.
        Include a recommendation to reorder and how many units should be ordered (reorder quantity: {product.reorder_quantity}).
        """
        
        content = self._generate_content(prompt)
        return self._convert_markdown_to_html(content)
    
    def _convert_markdown_to_html(self, text):
        """Convert markdown formatting to HTML
        
        Handles bold (**text**) and italic (*text*) formatting
        """
        # Convert bold: **text** to <strong>text</strong>
        bold_pattern = r'\*\*(.*?)\*\*'
        text = re.sub(bold_pattern, r'<strong>\1</strong>', text)
        
        # Convert italic: *text* to <em>text</em> (but avoid matching ** which is bold)
        # This regex looks for single asterisks not preceded or followed by another asterisk
        italic_pattern = r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)'
        text = re.sub(italic_pattern, r'<em>\1</em>', text)
        
        return text
    
    def generate_purchase_order_summary(self, purchase_order, supplier, items):
        """Generate a summary of a purchase order"""
        if not self.api_key:
            return f"Purchase Order #{purchase_order.id} for {supplier.name} containing {len(items)} items with total amount ${purchase_order.total_amount:.2f}."
        
        items_text = "\n".join([
            f"- {item.product.name} (SKU: {item.product.sku}): {item.quantity} units at ${item.unit_price:.2f} each = ${item.total_price:.2f}"
            for item in items
        ])
        
        prompt = f"""
        Purchase Order #{purchase_order.id} for {supplier.name}
        Order Date: {purchase_order.order_date.strftime('%Y-%m-%d')}
        Expected Delivery: {purchase_order.expected_delivery_date.strftime('%Y-%m-%d') if purchase_order.expected_delivery_date else 'Not specified'}
        Status: {purchase_order.status.upper()}
        
        Items:
        {items_text}
          Total Amount: ${purchase_order.total_amount:.2f}
        
        Please generate a concise, professional summary of this purchase order. Highlight any important details and suggest next steps based on the current status.
        """
        
        content = self._generate_content(prompt)
        return self._convert_markdown_to_html(content)
    
    def analyze_inventory_trends(self, product, transactions, days=30):
        """Analyze inventory trends for a product"""
        if not self.api_key:
            return f"Inventory analysis for {product.name}: Current stock level is {product.quantity_in_stock} units."
            
        # Filter transactions from the last 'days' days
        now = datetime.datetime.now()
        days_ago = now - datetime.timedelta(days=days)
        recent_transactions = [t for t in transactions if t.transaction_date >= days_ago]
        
        sales = [t for t in recent_transactions if t.transaction_type == 'sale']
        purchases = [t for t in recent_transactions if t.transaction_type == 'purchase']
        
        total_sales = sum(t.quantity for t in sales)
        total_purchases = sum(t.quantity for t in purchases)
        
        prompt = f"""
        Inventory Analysis for '{product.name}' (SKU: {product.sku}) over the past {days} days:
        
        Current stock level: {product.quantity_in_stock} units
        Reorder level: {product.reorder_level} units
        Reorder quantity: {product.reorder_quantity} units
        
        Recent activity:
        - Total units sold: {total_sales}
        - Total units purchased: {total_purchases}
        - Net change: {total_purchases - total_sales}
          Please analyze this data and provide:
        1. A brief assessment of the current inventory status
        2. Recommendation for inventory management (if stock is low, adequate, or excessive)
        3. Suggestions for optimizing the reorder level and quantity based on recent sales patterns
        """
        
        content = self._generate_content(prompt)
        return self._convert_markdown_to_html(content)
    
    def generate_irregular_activity_alert(self, product, transaction, avg_quantity):
        """Generate an alert for irregular inventory activity"""
        if not self.api_key:
            return f"Irregular activity detected for {product.name}. Transaction quantity: {transaction.quantity}, Average: {avg_quantity:.2f}"
            
        deviation = transaction.quantity / avg_quantity if avg_quantity > 0 else 0
        
        prompt = f"""
        Unusual inventory activity detected for '{product.name}' (SKU: {product.sku}):
        
        Transaction type: {transaction.transaction_type}
        Quantity: {transaction.quantity} units
        Date: {transaction.transaction_date.strftime('%Y-%m-%d %H:%M')}
          This transaction amount is {'significantly higher' if deviation > 2 else 'significantly lower' if deviation < 0.5 else 'unusual'} 
        compared to the average transaction quantity of {avg_quantity:.2f} units.
        
        Please generate a concise alert message explaining this irregular activity and suggesting possible explanations and actions to take.
        """
        
        content = self._generate_content(prompt)
        return self._convert_markdown_to_html(content)
    
    def predict_restock_timing(self, product, transactions):
        """Predict when a product will need to be restocked based on sales velocity"""
        import numpy as np
        from datetime import datetime, timedelta
        
        if not transactions:
            return {
                "days_until_restock": None,
                "predicted_date": None,
                "confidence": "low",
                "sales_velocity": 0
            }
        
        # Calculate daily sales rate (sales velocity)
        sale_transactions = [t for t in transactions if t.transaction_type == 'sale']
        if not sale_transactions:
            return {
                "days_until_restock": None,
                "predicted_date": None,
                "confidence": "low",
                "sales_velocity": 0
            }
        
        # Get date range
        dates = [t.transaction_date for t in sale_transactions]
        min_date = min(dates)
        max_date = max(dates)
        date_range = (max_date - min_date).days + 1
        
        # Calculate total sales and daily rate
        total_sales = sum(t.quantity for t in sale_transactions)
        daily_sales_rate = total_sales / max(date_range, 1)
        
        # Calculate days until restock needed
        if daily_sales_rate > 0:
            days_until_restock = int(product.quantity_in_stock / daily_sales_rate)
            predicted_date = datetime.now() + timedelta(days=days_until_restock)
            
            # Determine confidence based on data consistency
            quantities = [t.quantity for t in sale_transactions]
            if len(quantities) >= 5:
                coefficient_of_variation = np.std(quantities) / max(np.mean(quantities), 1)
                if coefficient_of_variation < 0.2:
                    confidence = "high"
                elif coefficient_of_variation < 0.5:
                    confidence = "medium"
                else:
                    confidence = "low"
            else:
                confidence = "low"
        else:
            days_until_restock = None
            predicted_date = None
            confidence = "low"
        
        return {
            "days_until_restock": days_until_restock,
            "predicted_date": predicted_date,
            "confidence": confidence,
            "sales_velocity": daily_sales_rate
        }
    
    def generate_inventory_recommendations(self, products, transactions, top_sellers, low_stock_products):
        """Generate AI-powered inventory recommendations"""
        if not self.api_key:
            return "Based on your current inventory data, consider restocking your top-selling products and reviewing slow-moving items."
        
        # Format top sellers for the prompt
        top_sellers_text = "\n".join([
            f"- {product.name}: {quantity} units sold"
            for product, quantity in top_sellers[:5]
        ]) if top_sellers else "No sales data available"
        
        # Format low stock products for the prompt
        low_stock_text = "\n".join([
            f"- {product.name}: Current stock {product.quantity_in_stock} units (below reorder level of {product.reorder_level})"
            for product in low_stock_products[:5]
        ]) if low_stock_products else "No products are below reorder levels"
        
        # Count products by category
        category_counts = {}
        for product in products:
            if product.category:
                category_name = product.category.name
                if category_name in category_counts:
                    category_counts[category_name] += 1
                else:
                    category_counts[category_name] = 1
        
        categories_text = "\n".join([
            f"- {category}: {count} products"
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        ]) if category_counts else "No category data available"
        
        prompt = f"""
        Based on the following inventory data, please provide 5 actionable recommendations for inventory management:
        
        Top selling products:
        {top_sellers_text}
        
        Products needing restock:
        {low_stock_text}
        
        Product categories:
        {categories_text}
        
        Total products in inventory: {len(products)}
        Total low stock products: {len(low_stock_products)}
          Please generate specific, actionable recommendations including:
        1. Which products to restock immediately
        2. Which product categories to expand or reduce
        3. How to optimize inventory turnover
        4. Potential bundling or promotion opportunities
        5. Inventory management process improvements
        Format your response as a numbered list with brief explanations.
        """
        
        content = self._generate_content(prompt)
        return self._convert_markdown_to_html(content)
