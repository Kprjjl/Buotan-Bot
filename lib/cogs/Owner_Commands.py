import discord
import asyncio
from discord.ext import commands
from ..db import db
extension_error_msgs = {
    1: lambda extension: f"'{extension}' cog not found.",
    2: lambda extension: f"'{extension}' cog not loaded.",
    3: lambda extension: f"'{extension}' has not setup fxn.",
    4: lambda extension: f"'{extension}''s setup fxn had an execution error."
}


class OwnerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def extension_cmds(self, cmd, extension):
        try:
            if cmd == "reload":
                self.bot.reload_extension(f'cogs.{extension}')
            elif cmd == "unload":
                self.bot.unload_extension(f'cogs.{extension}')
            elif cmd == "load":
                self.bot.load_extension(f'cogs.{extension}')
        except commands.ExtensionNotFound:
            return extension_error_msgs[1](extension)
        except commands.ExtensionNotLoaded:
            return extension_error_msgs[2](extension)
        except commands.NoEntryPointError:
            return extension_error_msgs[3](extension)
        except commands.ExtensionFailed:
            return extension_error_msgs[4](extension)
        except Exception as e:
            print(f"extension_cmds error: {e}")
        else:
            return 0

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, *, extension):
        result = self.extension_cmds("load", extension)
        if result == 0:
            await ctx.send(f'Loaded {extension}.')
        else:
            await ctx.send(result)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, *, extension):
        if extension != "Owner_Commands":
            result = self.extension_cmds("unload", extension)
            if result == 0:
                await ctx.send(f'Unloaded {extension}.')
            else:
                await ctx.send(result)
        else:
            await ctx.send("Owner Commands should not be unloaded.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx, *, extension):
        result = self.extension_cmds("reload", extension)
        if result == 0:
            await ctx.send(f"Reloaded {extension}.")
        else:
            await ctx.send(result)

    @commands.command(name="bot_act", hidden=True)
    @commands.is_owner()
    async def botactivity(self, ctx, *, activity=''):
        await self.bot.change_presence(activity=discord.Game(activity))

    @commands.command(name="bot_status", hidden=True)
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

    @commands.command(hidden=True)
    @commands.is_owner()
    async def closebot(self, ctx):
        await ctx.send("Going offline.")
        await self.bot.change_presence(status=discord.Status.offline)
        await asyncio.sleep(5)
        await self.bot.close()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def audiosurprise(self, ctx, guild_id, ch_id, file):  # only made this for surprise rick rolling and other
        guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
        channel = discord.utils.get(guild.channels, id=int(ch_id))
        vc = await channel.connect()
        vc.play(discord.FFmpegPCMAudio(f"./audio/{file}"))
        while True:
            await asyncio.sleep(.1)
            if not vc.is_playing():
                await vc.disconnect()
                break

    @commands.command(hidden=True)
    @commands.is_owner()
    async def dbcommit(self, ctx):
        db.commit()
        print(True)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Owner_Commands")


def setup(bot):
    bot.add_cog(OwnerCommands(bot))
