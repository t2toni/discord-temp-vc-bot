import discord
from discord.ext import commands
from discord import app_commands
import embeds

class PrefixModal(discord.ui.Modal, title="Set Server Prefix"):
    prefix = discord.ui.TextInput(
        label="New Prefix",
        style=discord.TextStyle.short,
        placeholder="e.g. !, ?, owo",
        required=True,
        max_length=5
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        new_prefix = self.prefix.value.strip()
        await self.bot.db.set_guild_prefix(interaction.guild_id, new_prefix)
        await interaction.response.send_message(
            embed=embeds.success_embed(f"Server prefix updated to `{new_prefix}`!"),
            ephemeral=True
        )

class SetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select Default Channel...",
        min_values=1,
        max_values=1
    )
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        # Check permissions
        permissions = channel.permissions_for(interaction.guild.me)
        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=embeds.error_embed(f"I don't have permission to send messages in {channel.mention}!"),
                ephemeral=True
            )
            return

        await self.bot.db.set_guild_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(
            embed=embeds.success_embed(f"Default channel set to {channel.mention}!"),
            ephemeral=True
        )

    @discord.ui.button(label="Set Custom Prefix", style=discord.ButtonStyle.primary, emoji="✏️")
    async def set_prefix_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PrefixModal(self.bot))


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Interactive bot setup and configuration")
    @app_commands.default_permissions(administrator=True)
    async def setup_cmd(self, interaction: discord.Interaction):
        config = await self.bot.db.get_guild_config(interaction.guild_id)
        
        prefix = config.prefix if config else "!"
        channel_id = config.default_channel_id if config else None
        channel_mention = f"<#{channel_id}>" if channel_id else "None"
        
        desc = (
            f"**Server Name:** {interaction.guild.name}\n"
            f"**Current Prefix:** `{prefix}`\n"
            f"**Default Channel:** {channel_mention}\n\n"
            "Use the dropdown below to set the default text channel for notifications and logs.\n"
            "Click the button to change the bot's command prefix."
        )
        
        embed = discord.Embed(
            title="⚙️ Server Configuration Setup",
            description=desc,
            color=discord.Color.blue()
        )
        
        view = SetupView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="config", description="Show the current server configuration")
    @app_commands.default_permissions(administrator=True)
    async def config_cmd(self, interaction: discord.Interaction):
        config = await self.bot.db.get_guild_config(interaction.guild_id)
        
        prefix = config.prefix if config else "!"
        channel_id = config.default_channel_id if config else None
        channel_mention = f"<#{channel_id}>" if channel_id else "Not configured"
        
        embed = discord.Embed(
            title="⚙️ Current Server Configuration",
            color=discord.Color.blue()
        )
        embed.add_field(name="Prefix", value=f"`{prefix}`", inline=True)
        embed.add_field(name="Default Channel", value=channel_mention, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setchannel", description="Set the default channel for the bot")
    @app_commands.default_permissions(administrator=True)
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        permissions = channel.permissions_for(interaction.guild.me)
        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=embeds.error_embed(f"I cannot send messages in {channel.mention}!"),
                ephemeral=True
            )
            return

        await self.bot.db.set_guild_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(
            embed=embeds.success_embed(f"Default channel updated to {channel.mention}!"),
            ephemeral=True
        )

    @app_commands.command(name="setprefix", description="Change the server command prefix")
    @app_commands.default_permissions(administrator=True)
    async def setprefix(self, interaction: discord.Interaction, new_prefix: str):
        if len(new_prefix) > 5:
            await interaction.response.send_message(
                embed=embeds.error_embed("Prefix cannot be longer than 5 characters!"),
                ephemeral=True
            )
            return
            
        await self.bot.db.set_guild_prefix(interaction.guild_id, new_prefix)
        await interaction.response.send_message(
            embed=embeds.success_embed(f"Server prefix updated to `{new_prefix}`!"),
            ephemeral=True
        )

    @app_commands.command(name="resetconfig", description="Reset the server configuration to defaults")
    @app_commands.default_permissions(administrator=True)
    async def resetconfig(self, interaction: discord.Interaction):
        await self.bot.db.reset_guild_config(interaction.guild_id)
        await interaction.response.send_message(
            embed=embeds.success_embed("Server configuration has been reset to defaults (Prefix: `!`, Channel: None)."),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Config(bot))
