import discord
from discord.ext import commands
from discord import app_commands
import embeds
import config
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Shows coins + level (self or mention)")
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await self.bot.db.get_or_create_user(user.id, interaction.guild_id, user.display_name)
        db_user = await self.bot.db.get_user(user.id)
        
        balance = db_user.balance if db_user else 0
        level = db_user.level if db_user else 1
        xp = db_user.xp if db_user else 0
        
        embed = embeds.balance_embed(user, balance)
        embed.description = f"**{user.display_name}** has **{balance} coins**\nLevel: {level} (XP: {xp})"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="top", description="Leaderboard of top 10 richest users")
    async def top(self, interaction: discord.Interaction):
        richest = await self.bot.db.get_richest_users(limit=10)
        
        if not richest:
            await interaction.response.send_message(embed=embeds.info_embed("🏆 Top 10 Richest Users", "No users found!"))
            return
            
        desc = ""
        for i, u in enumerate(richest, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
            desc += f"{medal} **{i}.** <@{u.id}> - **{u.balance} coins**\n"
            
        embed = embeds.get_embed("🏆 Top 10 Richest Users", desc, discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="give", description="Add coins to user (with logging)")
    @app_commands.default_permissions(administrator=True)
    async def give(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message(embed=embeds.error_embed("Amount must be greater than 0."), ephemeral=True)
            return
            
        await self.bot.db.get_or_create_user(user.id, interaction.guild_id, user.display_name)
        await self.bot.db.add_balance(user.id, amount)
        
        await interaction.response.send_message(embed=embeds.success_embed(f"Gave **{amount} coins** to {user.mention}."))
        
        if hasattr(self.bot, 'log_to_staff'):
            await self.bot.log_to_staff(f"💰 {interaction.user.mention} gave {amount} coins to {user.mention}.")

    @app_commands.command(name="take", description="Remove coins from user (with logging)")
    @app_commands.default_permissions(administrator=True)
    async def take(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message(embed=embeds.error_embed("Amount must be greater than 0."), ephemeral=True)
            return
            
        await self.bot.db.get_or_create_user(user.id, interaction.guild_id, user.display_name)
        await self.bot.db.remove_balance(user.id, amount)
        
        await interaction.response.send_message(embed=embeds.success_embed(f"Took **{amount} coins** from {user.mention}."))
        
        if hasattr(self.bot, 'log_to_staff'):
            await self.bot.log_to_staff(f"💰 {interaction.user.mention} took {amount} coins from {user.mention}.")

    @app_commands.command(name="coinflip", description="Bet virtual coins on a coin flip")
    @app_commands.describe(
        amount="Amount of virtual coins to bet",
        choice="Choose heads or tails"
    )
    @app_commands.choices(choice=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(
        self,
        interaction: discord.Interaction,
        amount: int,
        choice: app_commands.Choice[str]
    ):
        user_id = interaction.user.id
        await self.bot.db.get_or_create_user(user_id, interaction.guild_id, interaction.user.display_name)
        balance = await self.bot.db.get_balance(user_id)

        # Validate bet
        if amount <= 0:
            await interaction.response.send_message("❌ Bet must be greater than 0.", ephemeral=True)
            return

        if amount > balance:
            await interaction.response.send_message(f"❌ You only have **{balance:,} coins**.", ephemeral=True)
            return

        # Flip
        result = random.choice(["heads", "tails"])

        if choice.value == result:
            winnings = amount
            await self.bot.db.add_balance(user_id, winnings)
            new_balance = balance + winnings

            result_text = (
                f"🎉 **You won {winnings:,} coins!**\n"
                f"🪙 The coin landed on **{result.title()}**."
            )
            color = discord.Color.green()
        else:
            await self.bot.db.remove_balance(user_id, amount)
            new_balance = balance - amount

            result_text = (
                f"💀 **You lost {amount:,} coins!**\n"
                f"🪙 The coin landed on **{result.title()}**."
            )
            color = discord.Color.red()

        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=result_text,
            color=color
        )
        embed.add_field(name="Your choice", value=choice.name, inline=True)
        embed.add_field(name="Balance", value=f"💰 {new_balance:,}", inline=True)

        await interaction.response.send_message(embed=embed)

    @commands.command(name="cf", aliases=["coinflip_prefix"])
    async def cf_prefix(self, ctx, arg1: str, arg2: str = None):
        """Bet virtual coins on a coin flip using prefix command. Max bet: 250k."""
        user_id = ctx.author.id
        await self.bot.db.get_or_create_user(user_id, ctx.guild.id, ctx.author.display_name)
        balance = await self.bot.db.get_balance(user_id)

        valid_choices = ["h", "heads", "head", "t", "tails", "tail"]
        
        # Smart argument parsing
        if arg1.lower() in valid_choices and arg2 is not None:
            # User typed `!cf h all`
            choice_str = arg1
            amount_str = arg2
        else:
            # User typed `!cf all h` or `!cf all`
            amount_str = arg1
            choice_str = arg2 if arg2 is not None else "heads"

        # Parse choice
        choice = choice_str.lower()
        if choice in ["h", "heads", "head"]:
            choice_val = "heads"
        elif choice in ["t", "tails", "tail"]:
            choice_val = "tails"
        else:
            await ctx.send("❌ Invalid choice! Use `h` for heads or `t` for tails.")
            return

        # Parse amount
        amount_str = amount_str.lower()
        bet_amount = 0
        
        if amount_str == "all":
            bet_amount = balance
        elif amount_str == "half":
            bet_amount = balance // 2
        else:
            if amount_str.endswith("k"):
                try:
                    bet_amount = int(float(amount_str[:-1]) * 1000)
                except ValueError:
                    await ctx.send("❌ Invalid amount format.")
                    return
            else:
                try:
                    bet_amount = int(amount_str)
                except ValueError:
                    await ctx.send("❌ Invalid amount format.")
                    return
                    
        # Apply 250k max limit
        if bet_amount > 250000:
            bet_amount = 250000

        # Validate bet
        if bet_amount <= 0:
            await ctx.send("❌ Bet must be greater than 0.")
            return

        if bet_amount > balance:
            await ctx.send(f"❌ You only have **{balance:,} coins**.")
            return

        # Flip
        result = random.choice(["heads", "tails"])

        if choice_val == result:
            winnings = bet_amount
            await self.bot.db.add_balance(user_id, winnings)
            new_balance = balance + winnings

            result_text = (
                f"🎉 **You won {winnings:,} coins!**\n"
                f"🪙 The coin landed on **{result.title()}**."
            )
            color = discord.Color.green()
        else:
            await self.bot.db.remove_balance(user_id, bet_amount)
            new_balance = balance - bet_amount

            result_text = (
                f"💀 **You lost {bet_amount:,} coins!**\n"
                f"🪙 The coin landed on **{result.title()}**."
            )
            color = discord.Color.red()

        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=result_text,
            color=color
        )
        choice_name = "Heads" if choice_val == "heads" else "Tails"
        embed.add_field(name="Your choice", value=choice_name, inline=True)
        embed.add_field(name="Balance", value=f"💰 {new_balance:,}", inline=True)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
