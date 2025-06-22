"""
Discord Bot for Inventory Management System
This bot connects to your inventory management system and allows users
to add stocks and list products through a conversational interface.
"""
import os
import sys
import asyncio
import logging
from typing import Optional
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("discord-bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("discord-bot")

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialize bot with command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

# Add the parent directory to the Python path to import app modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import app services and custom services
try:
    from app.services.chatbot_service import ChatbotService
    
    # Import local modules (relative to discord-bot folder)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    
    from gemini_service import GeminiService
    from inventory_service import InventoryService
    
    chatbot_service = ChatbotService()
    gemini_service = GeminiService()
    inventory_service = InventoryService()
    
    logger.info("Successfully loaded all services")
except ImportError as e:
    logger.error(f"Error importing services: {e}")
    chatbot_service = None
    gemini_service = None
    inventory_service = None


@bot.event
async def on_ready():
    """Event handler for when the bot is ready and connected to Discord."""
    logger.info(f"{bot.user.name} has connected to Discord!")
    
    # Set bot status to show it's for inventory management
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="inventory levels"
        )
    )
    
    # Log connected guilds
    for guild in bot.guilds:
        logger.info(f"Connected to guild: {guild.name} (id: {guild.id})")


@bot.event
async def on_message(message):
    """Event handler for incoming messages."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check if message is in a DM or mentions the bot in a server
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user in message.mentions
    
    # Process message if it's a DM or mentions the bot
    if is_dm or is_mentioned:
        # Remove bot mention from the message content if present
        content = message.content
        if is_mentioned:
            # Remove the bot mention from the message
            content = content.replace(f'<@{bot.user.id}>', '').strip()
            content = content.replace(f'<@!{bot.user.id}>', '').strip()
        
        # Check if the message is empty after removing mentions
        if not content:
            return
        
        # Let the user know we're processing their message
        async with message.channel.typing():
            # Get inventory context for Gemini
            inventory_context = None
            if inventory_service:
                inventory_context = inventory_service.get_inventory_summary()
            
            # Use Gemini to detect intent if available
            intent_data = None
            if gemini_service:
                intent_data = gemini_service.extract_inventory_intent(content)
                logger.info(f"Detected intent: {intent_data}")
            
            # If we have a clear intent from Gemini, process it directly
            if intent_data and intent_data.get("intent") != "unknown":
                intent = intent_data.get("intent")
                entities = intent_data.get("entities", {})
                
                if intent == "add_stock" and "product_sku" in entities and "quantity" in entities:
                    # Format as a stock update message for the chatbot service
                    formatted_message = f"add {entities['quantity']} units to product {entities['product_sku']}"
                    if chatbot_service:
                        response_data = chatbot_service.process_message(formatted_message, str(message.author.id))
                        await message.reply(response_data["response"])
                        
                        # Store the product details for confirmation if needed
                        if response_data.get("needsConfirmation"):
                            message.author._last_product_request = response_data.get("product")
                    else:
                        await message.reply("I'm having trouble connecting to the inventory system.")
                
                elif intent == "remove_stock" and "product_sku" in entities and "quantity" in entities:
                    # Format as a stock removal message for the chatbot service
                    formatted_message = f"remove {entities['quantity']} units from product {entities['product_sku']}"
                    if chatbot_service:
                        response_data = chatbot_service.process_message(formatted_message, str(message.author.id))
                        await message.reply(response_data["response"])
                        
                        # Store the product details for confirmation if needed
                        if response_data.get("needsConfirmation"):
                            message.author._last_product_request = response_data.get("product")
                    else:
                        await message.reply("I'm having trouble connecting to the inventory system.")
                
                elif intent == "check_inventory" or intent == "product_info":
                    # Use either product_sku or product_name to search
                    search_term = entities.get("product_sku", entities.get("product_name", ""))
                    
                    if search_term and inventory_service:
                        # Search for products
                        products = inventory_service.search_products(search_term)
                        
                        if products:
                            # Format product information
                            product_info = "\n".join([
                                f"**{p['name']}** (SKU: {p['sku']})\n"
                                f"Stock: {p['quantity_in_stock']} units\n"
                                f"Price: ${p['unit_price']:.2f}\n"
                                for p in products[:3]  # Limit to 3 products
                            ])
                            
                            embed = discord.Embed(
                                title="Product Information",
                                description=f"Here's what I found for '{search_term}':",
                                color=discord.Color.blue()
                            )
                            
                            embed.add_field(
                                name="Products",
                                value=product_info or "No product details available",
                                inline=False
                            )
                            
                            await message.reply(embed=embed)
                        else:
                            await message.reply(f"I couldn't find any products matching '{search_term}'.")
                    else:
                        # Use the general query handler if we don't have a specific product to look up
                        if chatbot_service:
                            response_data = chatbot_service._handle_general_query(content)
                            await message.reply(response_data["response"])
                        elif gemini_service:
                            response = gemini_service.process_inventory_query(content, inventory_context)
                            await message.reply(response)
                        else:
                            await message.reply("I'm having trouble connecting to the inventory system.")
                else:
                    # Fall back to regular processing for other intents
                    if chatbot_service:
                        # Process the message using our existing chatbot service
                        response_data = chatbot_service.process_message(content, str(message.author.id))
                        
                        # Check if this is a request that needs confirmation
                        if response_data.get("needsConfirmation"):
                            await message.reply(response_data["response"])
                            
                            # Store the product details for confirmation
                            message.author._last_product_request = response_data.get("product")
                            
                        # Check if this is a confirmation message
                        elif response_data.get("isConfirmation") and hasattr(message.author, "_last_product_request"):
                            product = message.author._last_product_request
                            
                            # Process the stock update
                            update_result = chatbot_service.update_stock(
                                product["id"], 
                                product["quantity"] if product["operation"] == "add" else -product["quantity"],
                                str(message.author.id)
                            )
                            
                            await message.reply(update_result["message"])
                            
                            # Clear the stored request
                            delattr(message.author, "_last_product_request")
                            
                        # General response
                        else:
                            await message.reply(response_data["response"])
                    elif gemini_service:
                        # Use Gemini if chatbot service is not available
                        response = gemini_service.process_inventory_query(content, inventory_context)
                        await message.reply(response)
                    else:
                        await message.reply("I'm having trouble connecting to the inventory system. Please try again later.")
            
            # If we don't have a clear intent, use the chatbot service or Gemini
            else:
                if chatbot_service:
                    # Check if this is a confirmation message first
                    if chatbot_service._is_confirmation(content) and hasattr(message.author, "_last_product_request"):
                        product = message.author._last_product_request
                        
                        # Process the stock update
                        update_result = chatbot_service.update_stock(
                            product["id"], 
                            product["quantity"] if product["operation"] == "add" else -product["quantity"],
                            str(message.author.id)
                        )
                        
                        await message.reply(update_result["message"])
                        
                        # Clear the stored request
                        delattr(message.author, "_last_product_request")
                    else:
                        # Process the message using our existing chatbot service
                        response_data = chatbot_service.process_message(content, str(message.author.id))
                        
                        # Check if this is a request that needs confirmation
                        if response_data.get("needsConfirmation"):
                            await message.reply(response_data["response"])
                            
                            # Store the product details for confirmation
                            message.author._last_product_request = response_data.get("product")
                        else:
                            await message.reply(response_data["response"])
                elif gemini_service:
                    # Use Gemini if chatbot service is not available
                    response = gemini_service.process_inventory_query(content, inventory_context)
                    await message.reply(response)
                else:
                    await message.reply("I'm having trouble connecting to the inventory system. Please try again later.")
    
    # Process commands (for command-based interactions)
    await bot.process_commands(message)


@bot.command(name="inventory", help="Check inventory levels for products")
async def inventory(ctx, *, query: Optional[str] = None):
    """Command to check inventory levels."""
    if not query:
        # If no query is provided, show a summary of inventory
        if inventory_service:
            summary = inventory_service.get_inventory_summary()
            
            embed = discord.Embed(
                title="Inventory Summary",
                description=f"Total Products: {summary['total_products']}\nLow Stock Products: {summary['low_stock_count']}",
                color=discord.Color.blue()
            )
            
            # Add recent products
            if summary['products']:
                product_list = "\n".join([
                    f"• **{p['name']}** (SKU: {p['sku']}) - {p['quantity_in_stock']} units"
                    for p in summary['products']
                ])
                embed.add_field(name="Recent Products", value=product_list, inline=False)
            
            # Add low stock products
            low_stock = inventory_service.get_low_stock_products(5)
            if low_stock:
                low_stock_list = "\n".join([
                    f"• **{p['name']}** (SKU: {p['sku']}) - {p['quantity_in_stock']}/{p['reorder_level']} units"
                    for p in low_stock
                ])
                embed.add_field(name="Low Stock Alert", value=low_stock_list, inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("What would you like to know about the inventory? You can ask about specific products or general inventory status.")
        return
    
    # Let the user know we're processing their request
    async with ctx.typing():
        # Try to search for products matching the query
        if inventory_service:
            products = inventory_service.search_products(query)
            
            if products:
                # Create an embed for product information
                embed = discord.Embed(
                    title="Product Information",
                    description=f"Here's what I found for '{query}':",
                    color=discord.Color.blue()
                )
                
                for product in products[:5]:  # Limit to 5 products
                    embed.add_field(
                        name=f"{product['name']} (SKU: {product['sku']})",
                        value=f"Stock: {product['quantity_in_stock']} units\nPrice: ${product['unit_price']:.2f}\n{product.get('description', '')}",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                return
        
        # If no products found or if search fails, use the chatbot or Gemini service
        if chatbot_service:
            response_data = chatbot_service._handle_general_query(query)
            await ctx.send(response_data["response"])
        elif gemini_service and inventory_service:
            # Get inventory context for Gemini
            inventory_context = inventory_service.get_inventory_summary()
            response = gemini_service.process_inventory_query(query, inventory_context)
            await ctx.send(response)
        else:
            await ctx.send("I'm having trouble connecting to the inventory system. Please try again later.")


@bot.command(name="add_stock", help="Add stock to a product (e.g., !add_stock SKU-1234 20)")
async def add_stock(ctx, sku: str, quantity: int):
    """Command to add stock to a product."""
    if not sku or not quantity:
        await ctx.send("Please provide both SKU and quantity. Format: !add_stock SKU-1234 20")
        return
    
    # Format the message as it would be received by the chatbot service
    formatted_message = f"add {quantity} units to product {sku}"
    
    # Let the user know we're processing their request
    async with ctx.typing():
        if chatbot_service:
            response_data = chatbot_service.process_message(formatted_message, str(ctx.author.id))
            
            if response_data.get("needsConfirmation"):
                await ctx.send(response_data["response"])
                
                # Wait for confirmation
                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel and chatbot_service._is_confirmation(m.content)
                
                try:
                    await bot.wait_for('message', check=check, timeout=60.0)
                    
                    # Process the stock update
                    product = response_data.get("product")
                    update_result = chatbot_service.update_stock(
                        product["id"], 
                        product["quantity"],
                        str(ctx.author.id)
                    )
                    
                    await ctx.send(update_result["message"])
                    
                except asyncio.TimeoutError:
                    await ctx.send("Confirmation timed out. Stock update cancelled.")
            else:
                await ctx.send(response_data["response"])
        elif inventory_service:
            # Use the inventory service directly if chatbot service is not available
            product = inventory_service.get_product_by_sku(sku)
            
            if not product:
                await ctx.send(f"I couldn't find a product with SKU similar to '{sku}'. Please check the SKU and try again.")
                return
                
            # Ask for confirmation
            await ctx.send(f"I found {product['name']} with SKU-{product['sku']}. Current stock level is {product['quantity_in_stock']}. Would you like to add {quantity} units?")
            
            # Wait for confirmation
            def check(m):
                confirmation_words = ["yes", "confirm", "approved", "ok", "okay", "sure", "go ahead", "do it", "y", "yep", "yeah"]
                return m.author == ctx.author and m.channel == ctx.channel and any(word in m.content.lower() for word in confirmation_words)
            
            try:
                await bot.wait_for('message', check=check, timeout=60.0)
                
                # Process the stock update
                update_result = inventory_service.update_stock(sku, quantity, str(ctx.author.id))
                
                await ctx.send(update_result["message"])
                
            except asyncio.TimeoutError:
                await ctx.send("Confirmation timed out. Stock update cancelled.")
        else:
            await ctx.send("I'm having trouble connecting to the inventory system. Please try again later.")


@bot.command(name="remove_stock", help="Remove stock from a product (e.g., !remove_stock SKU-1234 10)")
async def remove_stock(ctx, sku: str, quantity: int):
    """Command to remove stock from a product."""
    if not sku or not quantity:
        await ctx.send("Please provide both SKU and quantity. Format: !remove_stock SKU-1234 10")
        return
    
    # Format the message as it would be received by the chatbot service
    formatted_message = f"remove {quantity} units from product {sku}"
    
    # Let the user know we're processing their request
    async with ctx.typing():
        if chatbot_service:
            response_data = chatbot_service.process_message(formatted_message, str(ctx.author.id))
            
            if response_data.get("needsConfirmation"):
                await ctx.send(response_data["response"])
                
                # Wait for confirmation
                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel and chatbot_service._is_confirmation(m.content)
                
                try:
                    await bot.wait_for('message', check=check, timeout=60.0)
                    
                    # Process the stock update
                    product = response_data.get("product")
                    update_result = chatbot_service.update_stock(
                        product["id"], 
                        -product["quantity"],
                        str(ctx.author.id)
                    )
                    
                    await ctx.send(update_result["message"])
                    
                except asyncio.TimeoutError:
                    await ctx.send("Confirmation timed out. Stock update cancelled.")
            else:
                await ctx.send(response_data["response"])
        elif inventory_service:
            # Use the inventory service directly if chatbot service is not available
            product = inventory_service.get_product_by_sku(sku)
            
            if not product:
                await ctx.send(f"I couldn't find a product with SKU similar to '{sku}'. Please check the SKU and try again.")
                return
                
            # Check if we have enough stock
            if product['quantity_in_stock'] < quantity:
                await ctx.send(f"I found {product['name']} with SKU-{product['sku']}, but there are only {product['quantity_in_stock']} units in stock. You cannot remove {quantity} units.")
                return
                
            # Ask for confirmation
            await ctx.send(f"I found {product['name']} with SKU-{product['sku']}. Current stock level is {product['quantity_in_stock']}. Would you like to remove {quantity} units?")
            
            # Wait for confirmation
            def check(m):
                confirmation_words = ["yes", "confirm", "approved", "ok", "okay", "sure", "go ahead", "do it", "y", "yep", "yeah"]
                return m.author == ctx.author and m.channel == ctx.channel and any(word in m.content.lower() for word in confirmation_words)
            
            try:
                await bot.wait_for('message', check=check, timeout=60.0)
                
                # Process the stock update
                update_result = inventory_service.update_stock(sku, -quantity, str(ctx.author.id))
                
                await ctx.send(update_result["message"])
                
            except asyncio.TimeoutError:
                await ctx.send("Confirmation timed out. Stock update cancelled.")
        else:
            await ctx.send("I'm having trouble connecting to the inventory system. Please try again later.")


@bot.command(name="low_stock", help="Show products with stock below reorder level")
async def low_stock(ctx, limit: Optional[int] = 10):
    """Show products with stock levels below their reorder point."""
    # Let the user know we're processing their request
    async with ctx.typing():
        if inventory_service:
            low_stock_products = inventory_service.get_low_stock_products(limit)
            
            if not low_stock_products:
                await ctx.send("Good news! There are no products below their reorder levels.")
                return
                
            # Create an embed for low stock products
            embed = discord.Embed(
                title="Low Stock Alert",
                description=f"These products have stock levels below their reorder points:",
                color=discord.Color.red()
            )
            
            for product in low_stock_products:
                embed.add_field(
                    name=f"{product['name']} (SKU: {product['sku']})",
                    value=f"Current Stock: **{product['quantity_in_stock']}**\nReorder Level: {product['reorder_level']}\nShortage: {product['shortage']} units",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("I'm having trouble connecting to the inventory system. Please try again later.")


@bot.command(name="search", help="Search for products by name or SKU")
async def search_products(ctx, *, query: str):
    """Search for products by name or SKU."""
    if not query:
        await ctx.send("Please provide a search term. Format: !search blue t-shirt")
        return
        
    # Let the user know we're processing their request
    async with ctx.typing():
        if inventory_service:
            products = inventory_service.search_products(query)
            
            if not products:
                await ctx.send(f"No products found matching '{query}'.")
                return
                
            # Create an embed for search results
            embed = discord.Embed(
                title="Product Search Results",
                description=f"Found {len(products)} products matching '{query}':",
                color=discord.Color.green()
            )
            
            for product in products[:8]:  # Limit to 8 products
                embed.add_field(
                    name=f"{product['name']} (SKU: {product['sku']})",
                    value=f"Stock: {product['quantity_in_stock']} units\nPrice: ${product['unit_price']:.2f}\n{product.get('description', '')[:100]}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("I'm having trouble connecting to the inventory system. Please try again later.")


@bot.command(name="help_inventory", help="Get help with inventory commands")
async def help_inventory(ctx):
    """Display help information for inventory commands."""
    embed = discord.Embed(
        title="Inventory Management Bot Help",
        description="Here are the commands you can use to manage inventory:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="!inventory [query]",
        value="Check inventory levels or ask general inventory questions. Without a query, it shows a summary.",
        inline=False
    )
    
    embed.add_field(
        name="!add_stock [SKU] [quantity]",
        value="Add stock to a product (e.g., !add_stock SKU-1234 20)",
        inline=False
    )
    
    embed.add_field(
        name="!remove_stock [SKU] [quantity]",
        value="Remove stock from a product (e.g., !remove_stock SKU-1234 10)",
        inline=False
    )
    
    embed.add_field(
        name="!low_stock [limit]",
        value="Show products with stock below reorder level (optional: specify max number of results)",
        inline=False
    )
    
    embed.add_field(
        name="!search [query]",
        value="Search for products by name or SKU (e.g., !search blue t-shirt)",
        inline=False
    )
    
    embed.add_field(
        name="Conversational Interface",
        value="You can also interact with the bot by mentioning it or in DMs with natural language like 'add 10 units to SKU-1234' or 'How many units of SKU-5678 do we have?'",
        inline=False
    )
    
    embed.set_footer(text=f"Bot Version 1.0 | {datetime.now().strftime('%Y-%m-%d')}")
    
    await ctx.send(embed=embed)


if __name__ == "__main__":
    if not TOKEN:
        logger.error("Discord token not found. Please set the DISCORD_TOKEN environment variable.")
        sys.exit(1)
    
    if not chatbot_service:
        logger.warning("ChatbotService could not be loaded. Some functionality may be limited.")
    
    # Start the bot
    bot.run(TOKEN)
