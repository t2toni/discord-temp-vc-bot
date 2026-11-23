import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import random

MESSAGE_COOLDOWN_SECONDS = 60
VC_REWARD_MINUTES = 10

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc_rewards.start()

    def cog_unload(self):
        self.vc_rewards.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        await self.bot.db.get_or_create_user(message.author.id, message.guild.id, message.author.display_name)
        
        last_message_time = await self.bot.db.get_last_message_time(message.author.id)
        
        now = datetime.utcnow()
        if last_message_time is None or (now - last_message_time).total_seconds() >= MESSAGE_COOLDOWN_SECONDS:
            await self.bot.db.increment_message_count(message.author.id)
            
            # Arcane XP amount: 15-25 XP per message
            xp_amount = random.randint(15, 25)
            await self.bot.db.add_xp(message.author.id, xp_amount)

    @tasks.loop(minutes=VC_REWARD_MINUTES)
    async def vc_rewards(self):
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot or member.voice.self_deaf or member.voice.deaf:
                        continue
                    
                    await self.bot.db.get_or_create_user(member.id, guild.id, member.display_name)
                    # Award XP for voice chat (e.g. 50 XP per 10 mins)
                    await self.bot.db.add_xp(member.id, 50)
                    # We could also increment vc_minutes here if we had a dedicated method, 
                    # but for now, rewarding coins is the primary mechanic.

    @vc_rewards.before_loop
    async def before_vc_rewards(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Events(bot))
