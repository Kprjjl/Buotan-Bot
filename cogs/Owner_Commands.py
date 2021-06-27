import discord
import asyncio
from discord.ext import commands


class OwnerCommands(commands.Cog):
    def __init__self(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def changeprefix(self, ctx, prefix):
        with open('prefix', 'w') as pf:
            pf.write(f'{prefix}')
            await ctx.send(f'Prefix changed to: {prefix}')

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx, *, extension):
        self.bot.load_extension(f'cogs.{extension}')
        print(f'Loaded {extension}.')

    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx, *, extension):
        if extension != "Owner Commands":
            self.bot.unload_extension(f'cogs.{extension}')
            print(f'Unloaded {extension}.')
        else:
            await ctx.send("Owner Commands should not be unloaded.")

    @commands.command(name="bot_act")
    @commands.is_owner()
    async def botactivity(self, ctx, *, activity=''):
        await self.bot.change_presence(activity=discord.Game(activity))

    @commands.command(name="bot_status")
    @commands.is_owner()
    async def botstatus(self, ctx, *, status="online"):
        if status == "online":
            await self.bot.change_presence(status=discord.Status.online)
        elif status == "idle":
            await self.bot.change_presence(status=discord.Status.idle)
        elif status == "offline":
            await self.bot.change_presence(status=discord.Status.offline)
        elif status == "DND":
            await self.bot.change_presence(status=discord.Status.do_not_disturb)
        else:
            await ctx.send(f"Invalid status: {status}")

    @commands.command()
    @commands.is_owner()
    async def closebot(self, ctx):
        await ctx.send("Going offline.")
        await self.bot.change_presence(status=discord.Status.offline)
        await asyncio.sleep(5)
        await self.bot.close()


def setup(bot):
    bot.add_cog(OwnerCommands(bot))
