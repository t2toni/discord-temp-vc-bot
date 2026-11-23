import discord
from discord.ext import commands
from config import DISCORD_TOKEN, STAFF_CHANNEL_ID
from database import Database
import embeds
import asyncio
import os

# Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

async def get_prefix(bot, message):
    if not message.guild:
        return "!"
    try:
        config = await bot.db.get_guild_config(message.guild.id)
        return config.prefix if config else "!"
    except Exception:
        return "!"

# Bot instance
bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None, strip_after_prefix=True)
bot.db = Database()


# Admin logging function
async def log_to_staff(message: str):
    """Send a log message to the staff channel."""
    if STAFF_CHANNEL_ID == 0:
        return
    
    for guild in bot.guilds:
        channel = guild.get_channel(STAFF_CHANNEL_ID)
        if channel:
            try:
                embed = embeds.info_embed("📝 Admin Log", message)
                await channel.send(embed=embed)
            except Exception as e:
                print(f"[Log Error] Could not send to staff channel: {e}")
            break


async def log_to_staff_embed(embed: discord.Embed):
    """Send a custom embed to the staff channel."""
    if STAFF_CHANNEL_ID == 0:
        return
    
    for guild in bot.guilds:
        channel = guild.get_channel(STAFF_CHANNEL_ID)
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"[Log Error] Could not send embed to staff channel: {e}")
            break

bot.log_to_staff = log_to_staff
bot.log_to_staff_embed = log_to_staff_embed


# Cog loader
async def load_cogs():
    """Load all cogs from the cogs directory."""
    cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
    
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            cog_name = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(cog_name)
                print(f"✅ Loaded cog: {cog_name}")
            except Exception as e:
                print(f"❌ Failed to load cog {cog_name}: {e}")


# Global error handlers
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Global handler for slash command errors."""
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            embed=embeds.error_embed(f"⏱️ Command on cooldown. Try again in {error.retry_after:.1f}s"),
            ephemeral=True
        )
    elif isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message(
            embed=embeds.error_embed("🚫 You don't have permission to use this command!"),
            ephemeral=True
        )
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        await interaction.response.send_message(
            embed=embeds.error_embed("🤖 I don't have the required permissions to do that!"),
            ephemeral=True
        )
    elif isinstance(error, discord.app_commands.CheckFailure):
        await interaction.response.send_message(
            embed=embeds.error_embed("❌ You don't meet the requirements to use this command!"),
            ephemeral=True
        )
    else:
        # Unknown error
        print(f"[Command Error] {error}")
        await interaction.response.send_message(
            embed=embeds.error_embed("⚠️ An unexpected error occurred!"),
            ephemeral=True
        )
        # Log to staff
        await log_to_staff(f"⚠️ Command error: {error}")


@bot.event
async def on_command_error(ctx, error):
    """Global handler for prefix command errors."""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=embeds.error_embed("🚫 You don't have permission to use this command!"))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=embeds.error_embed("🤖 I don't have the required permissions!"))
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=embeds.error_embed(f"⏱️ Command on cooldown. Try again in {error.retry_after:.1f}s"))
    else:
        print(f"[Command Error] {error}")
        await ctx.send(embed=embeds.error_embed("⚠️ An unexpected error occurred!"))
        await log_to_staff(f"⚠️ Prefix command error: {error}")


@bot.event
async def setup_hook():
    """Called when the bot is starting up."""
    # Initialize database first
    await bot.db.init()
    print("✅ Database initialized")
    
    await load_cogs()
    
    # Sync slash commands
    try:
        guild = discord.Object(id=1487009333085601834)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ Synced {len(synced)} slash commands to guild 1487009333085601834")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


# Simple help command
@bot.command(name="help")
async def help_command(ctx):
    """Show available commands."""
    embed = embeds.get_embed(
        "📚 Bot Commands",
        "**Slash Commands:**\n"
        "`/ping` — Check bot latency\n"
        "`/balance [@user]` — Check coin balance\n"
        "`/userinfo [@user]` — View user stats & level\n"
        "`/top` — View richest users leaderboard\n"
        "`/shop` — View shop items\n"
        "`/buyroyal` — Purchase Royal Role (500 coins)\n\n"
        "**Admin Commands:**\n"
        "`/give @user <amount>` — Give coins (Admin only)\n"
        "`/take @user <amount>` — Remove coins (Admin only)\n"
        "`/sync` — Sync slash commands (Owner only)",
        discord.Color.blue()
    )
    await ctx.send(embed=embed)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN not set. Check your .env file.")
    bot.run(DISCORD_TOKEN)
