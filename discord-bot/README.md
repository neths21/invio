# Inventory Management Discord Bot

This Discord bot allows you to manage your inventory system directly from Discord. It connects to your existing inventory management system and leverages Google's Gemini AI for natural language processing capabilities.

## Features

- **Natural Language Processing**: Interact with your inventory using natural language
- **Stock Management**: Add or remove stock using simple commands
- **Inventory Queries**: Check inventory levels, search for products, and view low stock alerts
- **AI-Powered Responses**: Get intelligent responses to inventory-related questions

## Commands

- `!inventory [query]` - Check inventory levels or ask general inventory questions
- `!add_stock [SKU] [quantity]` - Add stock to a product
- `!remove_stock [SKU] [quantity]` - Remove stock from a product
- `!low_stock [limit]` - Show products with stock below reorder level
- `!search [query]` - Search for products by name or SKU
- `!help_inventory` - Display help for inventory commands

## Conversational Interface

You can also interact with the bot by mentioning it in a channel or sending direct messages. Examples:

- "Add 20 units to product SKU-1234"
- "Remove 10 units from SKU-5678"
- "How many blue t-shirts do we have in stock?"
- "Show me products with low stock"

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r discord-bot/requirements.txt
   ```
3. Create a `.env` file based on `.env.example` with your Discord token and Gemini API key:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   DISCORD_GUILD=your_server_name_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
4. Run the bot:
   ```
   python discord-bot/bot.py
   ```

## Discord Bot Creation

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under the "Token" section, click "Copy" to get your bot token for the `.env` file
5. In the "Privileged Gateway Intents" section, enable:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
6. Go to the "OAuth2" tab, then "URL Generator"
7. Select the scopes: `bot` and `applications.commands`
8. Select permissions: 
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Use Slash Commands
9. Copy the generated URL and open it in your browser to add the bot to your server

## Getting a Gemini API Key

1. Go to the [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add the key to your `.env` file

## Integration with Inventory System

This bot is designed to work with the existing inventory management system. It uses the `ChatbotService` from the main application to process user messages and interact with the database.

## Requirements

- Python 3.8+
- discord.py
- google-generativeai
- python-dotenv
- Access to the main inventory management system

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Discord bot tokens and API keys should be treated as sensitive credentials
- Consider implementing role-based access control for inventory management commands

## License

This project is licensed under the MIT License - see the LICENSE file for details.
