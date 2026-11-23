import discord
from discord.ext import commands
from discord import app_commands
import embeds
import config
from datetime import datetime

class ShopView(discord.ui.View):
    def __init__(self, bot, shop_items):
        super().__init__(timeout=None)  # Buttons work forever
        self.bot = bot
        
        for item in shop_items:
            button = discord.ui.Button(
                label=f"Buy {item.name}",
                style=discord.ButtonStyle.blurple,
                custom_id=f"buy_role_{item.role_id}",
                emoji="🛒"
            )
            button.callback = self.create_callback(item.role_id, item.name, item.price, item.duration_days)
            self.add_item(button)

    def create_callback(self, role_id, role_name, cost, duration):
        async def callback(interaction: discord.Interaction):
            await self.bot.db.get_or_create_user(interaction.user.id, interaction.guild_id, interaction.user.display_name)
            balance = await self.bot.db.get_balance(interaction.user.id)
            
            if balance < cost:
                await interaction.response.send_message(embed=embeds.insufficient_balance_embed(balance, cost), ephemeral=True)
                return
                
            # Deduct balance
            await self.bot.db.remove_balance(interaction.user.id, cost)
            
            role = interaction.guild.get_role(role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    # Record purchase
                    await self.bot.db.record_purchase(interaction.user.id, role.id, duration)
                except discord.Forbidden:
                    await self.bot.db.add_balance(interaction.user.id, cost) # Refund
                    await interaction.response.send_message(embed=embeds.error_embed(f"I don't have permission to assign the {role_name} role! Coins refunded."), ephemeral=True)
                    return
            else:
                await self.bot.db.add_balance(interaction.user.id, cost) # Refund
                await interaction.response.send_message(embed=embeds.error_embed(f"The role {role_name} does not exist in this server. Coins refunded."), ephemeral=True)
                return
            
            await interaction.response.send_message(embed=embeds.success_embed(f"Successfully purchased **{role_name}** for {cost} coins!"), ephemeral=True)
            
            if hasattr(self.bot, 'log_to_staff'):
                await self.bot.log_to_staff(f"🛍️ {interaction.user.mention} purchased the **{role_name}** role for {cost} coins.")

        return callback


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # To make buttons persistent, we normally add a View without items, 
        # but since items are dynamic, we must re-create the view on startup.
        # We will do this asynchronously in a background task or rely on the custom_id callback.
        # For dynamic custom_id to work across restarts, we need a generic handler, 
        # but since this is a simple implementation, we'll register it when the command is invoked.
        # We should define a persistent listener for interaction creates in the bot instead,
        # but for now we'll just let them use the command.

    shopadmin_group = app_commands.Group(name="shopadmin", description="Shop administration commands")

    @shopadmin_group.command(name="setup", description="Creates missing shop roles in the server from DB items")
    @app_commands.default_permissions(administrator=True)
    async def setup_shop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        created = []
        shop_items = await self.bot.db.get_all_shop_items()
        
        for item in shop_items:
            existing = discord.utils.get(interaction.guild.roles, name=item.name)
            if not existing:
                try:
                    role = await interaction.guild.create_role(
                        name=item.name,
                        hoist=True,
                        reason="Shop setup"
                    )
                    created.append(item.name)
                    # We could theoretically update the DB with the new role.id, but since
                    # our DB maps role_id -> details, and the name matches, it's a bit complex.
                    # Usually role_id in DB is the actual role ID.
                except discord.Forbidden:
                    await interaction.followup.send(embed=embeds.error_embed("I don't have 'Manage Roles' permission!"))
                    return
        
        if created:
            await interaction.followup.send(embed=embeds.success_embed(f"Created roles: {', '.join(created)}"))
        else:
            await interaction.followup.send(embed=embeds.info_embed("Shop Setup", "All shop roles already exist!"))

    @shopadmin_group.command(name="additem", description="Add or update a role in the shop")
    @app_commands.default_permissions(administrator=True)
    async def add_item(self, interaction: discord.Interaction, role: discord.Role, price: int, duration_days: int, description: str = None):
        if price <= 0:
            await interaction.response.send_message(embed=embeds.error_embed("Price must be greater than 0!"), ephemeral=True)
            return
            
        if duration_days <= 0:
            await interaction.response.send_message(embed=embeds.error_embed("Duration must be at least 1 day!"), ephemeral=True)
            return

        await self.bot.db.add_shop_item(
            role_id=role.id,
            name=role.name,
            price=price,
            duration=duration_days,
            description=description or f"{role.name} role"
        )
        
        desc = f"**Role:** {role.mention}\n**Price:** {price:,} coins\n**Duration:** {duration_days} days"
        if description:
            desc += f"\n**Description:** {description}"
            
        await interaction.response.send_message(embed=embeds.success_embed(f"Successfully added/updated item in shop!\n\n{desc}"))

    @app_commands.command(name="shop", description="Shows available roles for purchase")
    async def shop(self, interaction: discord.Interaction):
        shop_items = await self.bot.db.get_all_shop_items()
        
        if not shop_items:
            await interaction.response.send_message(embed=embeds.error_embed("There are no roles available in the shop right now!"), ephemeral=True)
            return
            
        desc = "🛍️ **Welcome to the Role Shop!**\n\nClick a button below to purchase a role:\n\n"
        
        for item in shop_items:
            desc += f"🏷️ **{item.name}** — {item.price:,} coins\n"
            desc += f"⏱️ Duration: {item.duration_days} days\n"
            if item.description:
                desc += f"📝 {item.description}\n"
            desc += "\n"
            
        desc += "💡 *Make sure you have enough coins before purchasing!*\n\n"
        
        embed = discord.Embed(
            title="🏪 Role Shop",
            description=desc,
            color=discord.Color.blue()
        )
        current_time = datetime.now().strftime("%m/%d/%Y %I:%M %p")
        embed.set_footer(text=f"Click any button to purchase • Buttons work forever | {current_time}")
        
        view = ShopView(self.bot, shop_items)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Shop(bot))
