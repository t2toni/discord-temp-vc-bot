import os
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
# Railway environment variables are already in os.environ
load_dotenv(override=False)

# Get from environment (Railway sets these, or .env file locally)
# Get from environment (Railway sets these, or .env file locally)
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
COMMAND_PREFIX = os.environ.get("COMMAND_PREFIX", "!")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "bot.db")

# STAFF_CHANNEL_ID - must be a valid integer
staff_channel_id_str = os.environ.get("STAFF_CHANNEL_ID", "0")
try:
    STAFF_CHANNEL_ID = int(staff_channel_id_str)
except ValueError:
    STAFF_CHANNEL_ID = 0  # Default if invalid

# Shop Configuration - Define roles and their prices
SHOP_ROLES = {
    "Royal": {"price": 500, "color": 0xFFD700, "description": "👑 Exclusive Royal status"},
    "MVP": {"price": 1000, "color": 0xFF6B6B, "description": "🏆 Most Valuable Player"},
    "VIP": {"price": 250, "color": 0x9B59B6, "description": "💎 Very Important Person"},
    "Elite": {"price": 750, "color": 0x3498DB, "description": "🔥 Elite member status"},
}

# List of role names that can be purchased (used for seasonal resets)
PURCHASABLE_ROLES = list(SHOP_ROLES.keys())

# Role purchase duration (in days)
ROLE_DURATION_DAYS = 30  # Change to 7, 14, or 60 as needed
