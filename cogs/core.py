import discord
from discord.ext import commands
from discord import app_commands
import embeds

class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Shows bot latency in ms")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(embed=embeds.ping_embed(latency))

    @app_commands.command(name="profile", description="Shows your detailed profile and stats")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await self.bot.db.get_or_create_user(user.id, interaction.guild_id, user.display_name)
        db_user = await self.bot.db.get_user(user.id)
        
        balance = db_user.balance if db_user else 0
        joined_at = db_user.joined_at.strftime("%b %d, %Y") if db_user and db_user.joined_at else "Unknown"
        level = db_user.level if db_user else 1
        xp = db_user.xp if db_user else 0
        msg_count = db_user.message_count if db_user else 0
        vc_minutes = db_user.vc_minutes if db_user else 0
        daily_streak = db_user.daily_streak if db_user and db_user.daily_streak else 0
        
        # Calculate Rank Title
        if level >= 100: rank_title = "👑 Legend"
        elif level >= 50: rank_title = "🏆 Master"
        elif level >= 20: rank_title = "🌟 Veteran"
        else: rank_title = "👤 Member"
        
        # Calculate XP Progress
        total_xp_for_current = sum(5 * (i ** 2) + 50 * i + 100 for i in range(level))
        xp_for_next = 5 * (level ** 2) + 50 * level + 100
        
        current_progress = xp - total_xp_for_current
        needed_for_next = xp_for_next - current_progress
        
        # Format VC Time
        hours = vc_minutes // 60
        mins = vc_minutes % 60
        
        embed = discord.Embed(
            title=f"👤 {user.display_name}'s Profile",
            color=discord.Color.dark_theme()
        )
        if user.display_avatar:
            embed.set_thumbnail(url=user.display_avatar.url)
            
        embed.description = f"{rank_title} • Level {level}\n\n"
        
        embed.description += "**💰 Economy**\n"
        embed.description += f"**Balance:** {balance:,} coins\n"
        embed.description += f"**Daily Streak:** {daily_streak} days\n"
        embed.description += f"**Total Messages:** {msg_count:,}\n"
        embed.description += f"**Total VC Time:** {hours}h {mins}m\n\n"
        
        embed.description += "**⭐ Leveling**\n"
        embed.description += f"**Level:** {level}\n"
        embed.description += f"**XP:** {xp:,} total\n"
        embed.description += f"**Progress:** {current_progress:,}/{xp_for_next:,} XP\n"
        embed.description += f"**Next Level:** {needed_for_next:,} XP needed\n\n"
        
        active_purchases = await self.bot.db.get_user_active_purchases(user.id)
        if active_purchases:
            embed.description += "**🛒 Active Purchased Roles**\n"
            for p in active_purchases:
                role = interaction.guild.get_role(p['role_id'])
                role_name = role.name if role else "Unknown Role"
                embed.description += f"🏷️ **{role_name}** — {p['days_remaining']} days left\n"
        
        from datetime import datetime
        current_time = datetime.now().strftime("%m/%d/%Y %I:%M %p")
        embed.set_footer(text=f"Member since {joined_at} | {current_time}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sync", description="Syncs slash commands globally")
    @commands.is_owner()
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        synced = await self.bot.tree.sync()
        await interaction.followup.send(embed=embeds.success_embed(f"Synced {len(synced)} commands globally."), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Core(bot))
