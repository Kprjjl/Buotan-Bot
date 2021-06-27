import discord
import asyncio
from discord.ext import commands


class OwnerCommands(commands.Cog):
    def __init__self(self, bot):
        self.bot = bot

    pass


def setup(bot):
    bot.add_cog(OwnerCommands(bot))
