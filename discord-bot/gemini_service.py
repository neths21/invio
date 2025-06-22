"""
Gemini AI integration for the Discord bot.
This module handles the integration with Google's Gemini API
for natural language processing capabilities.
"""
import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger("discord-bot.gemini")

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure the Gemini API client
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini API configured successfully")
    except Exception as e:
        logger.error(f"Error configuring Gemini API: {e}")
else:
    logger.warning("Gemini API key not found. Advanced NLP features will be limited.")


class GeminiService:
    """Service for interacting with Google's Gemini AI."""
    
    def __init__(self):
        """Initialize the Gemini service."""
        self.model = None
        self.conversation = None
        
        if GEMINI_API_KEY:
            try:
                # Use the Gemini Pro model for natural language processing
                self.model = genai.GenerativeModel('gemini-pro')
                # Start a conversation history
                self.conversation = self.model.start_chat(history=[])
                logger.info("Gemini model initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Gemini model: {e}")
    
    def process_inventory_query(self, query: str, inventory_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process an inventory-related query using Gemini AI.
        
        Args:
            query: The user's inventory-related query
            inventory_context: Optional contextual information about the inventory
            
        Returns:
            A response string from Gemini
        """
        if not self.model or not self.conversation:
            return "I'm currently unable to process natural language queries. Please use specific commands instead."
        
        try:
            # Create a system prompt with inventory context
            system_prompt = """
            You are an AI assistant for an inventory management system. Answer the user's question about inventory.
            Only respond with information about inventory management, products, stock levels, etc.
            Keep responses concise and helpful. If you don't know an answer, ask for more specific information.
            """
            
            # Add inventory context if available
            if inventory_context:
                # Format product information if available
                product_info = ""
                if "products" in inventory_context:
                    product_info = "\nProduct Information:\n" + "\n".join([
                        f"• {p.get('name', 'Unknown')}\n"
                        f"  SKU: {p.get('sku', 'Unknown')}\n"
                        f"  Stock: {p.get('quantity_in_stock', 0)} units"
                        for p in inventory_context.get("products", [])[:5]  # Limit to 5 products
                    ])
                
                system_prompt += f"""
                INVENTORY CONTEXT:
                Total products in inventory: {inventory_context.get('total_products', 'Unknown')}
                Products with low stock: {inventory_context.get('low_stock_count', 'Unknown')}
                {product_info}
                """
            
            # Send the query to Gemini with the context
            full_prompt = f"{system_prompt}\n\nUSER QUERY:\n{query}"
            response = self.conversation.send_message(full_prompt)
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error processing query with Gemini: {e}")
            return "Sorry, I encountered an error processing your request. Please try again later or use specific commands."
    
    def extract_inventory_intent(self, message: str) -> Dict[str, Any]:
        """
        Use Gemini to extract inventory-related intents from user messages.
        
        Args:
            message: The user's message
            
        Returns:
            A dictionary containing the extracted intent and entities
        """
        if not self.model:
            return {"intent": "unknown", "entities": {}}
        
        try:
            prompt = """
            Extract the inventory management intent and entities from the following message.
            Return a JSON object with the following structure:
            {
                "intent": one of ["check_inventory", "add_stock", "remove_stock", "product_info", "unknown"],
                "entities": {
                    "product_sku": "SKU if mentioned",
                    "quantity": number if mentioned,
                    "product_name": "product name if mentioned"
                }
            }
            
            For example:
            - "add 20 units to product SKU-1234" should return:
              {"intent": "add_stock", "entities": {"product_sku": "SKU-1234", "quantity": 20}}
              
            - "how many units of blue t-shirts do we have?" should return:
              {"intent": "check_inventory", "entities": {"product_name": "blue t-shirts"}}
              
            - "remove 15 items from SKU-5678" should return:
              {"intent": "remove_stock", "entities": {"product_sku": "SKU-5678", "quantity": 15}}
              
            MESSAGE:
            """
            
            response = self.model.generate_content(f"{prompt}\n{message}")
            
            # Try to parse the response as JSON
            try:
                import json
                from json import JSONDecodeError
                
                # The response might include markdown code blocks, so extract just the JSON part
                text = response.text
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                result = json.loads(text)
                return result
            except (JSONDecodeError, IndexError) as e:
                logger.warning(f"Error parsing Gemini JSON response: {e}")
                logger.warning(f"Raw response: {response.text}")
                return {"intent": "unknown", "entities": {}}
            
        except Exception as e:
            logger.error(f"Error extracting intent with Gemini: {e}")
            return {"intent": "unknown", "entities": {}}
