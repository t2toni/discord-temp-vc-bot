import discord
from datetime import datetime


def get_embed(title, description, color=discord.Color.blue()):
    """Base embed template with consistent styling."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now()
    )
    return embed


def success_embed(action):
    """Green embed for successful operations."""
    return get_embed("✅ Success", action, discord.Color.green())


def error_embed(reason):
    """Red embed for errors."""
    return get_embed("❌ Error", reason, discord.Color.red())


def warning_embed(message):
    """Yellow embed for warnings/notifications."""
    return get_embed("⚠️ Warning", message, discord.Color.yellow())


def info_embed(title, content):
    """Blue embed for general information."""
    return get_embed(title, content, discord.Color.blue())


# Specific command embeds

def ping_embed(latency):
    """Embed for ping command."""
    return get_embed(
        "🏓 Pong!",
        f"Bot latency: **{latency}ms**",
        discord.Color.green() if latency < 100 else discord.Color.yellow() if latency < 250 else discord.Color.red()
    )


def balance_embed(member, balance):
    """Embed for balance command."""
    embed = get_embed(
        "💰 Balance",
        f"**{member.display_name}** has **{balance} coins**",
        discord.Color.gold()
    )
    embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
    return embed


def userinfo_embed(member, balance, joined_at):
    """Embed for userinfo command."""
    embed = get_embed(
        "👤 User Information",
        f"**User:** {member.display_name}\n**Balance:** {balance} coins\n**Joined:** {joined_at}",
        discord.Color.purple()
    )
    embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
    return embed


def royal_purchase_embed(balance, cost):
    """Embed for Royal Role purchase confirmation."""
    return get_embed(
        "👑 Royal Role Purchase",
        f"Are you sure you want to purchase the Royal Role for **{cost} coins**?\n\n"
        f"Your current balance: **{balance} coins**\n"
        f"Balance after purchase: **{balance - cost} coins**",
        discord.Color.gold()
    )


def royal_success_embed(member):
    """Embed for successful Royal Role purchase."""
    return success_embed(
        f"Purchase successful! {member.display_name} is now a Royal member! 👑\n"
        f"500 coins have been deducted from your balance."
    )


def insufficient_balance_embed(current, required):
    """Embed for insufficient balance error."""
    return error_embed(
        f"You don't have enough coins!\nRequired: **{required}**, You have: **{current}**"
    )
