from discord.ext.commands import Cog, command, has_permissions, CheckFailure, MissingPermissions
from discord.utils import get
from discord import Color
from apscheduler.triggers.cron import CronTrigger
from ..db import db


class Misc(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("misc")

    @command(name="prefix",
             brief="Change bot prefix for this server (default: 'b!')")
    @has_permissions(manage_guild=True)
    async def change_prefix(self, ctx, new="b!"):
        if len(new) > 5:
            await ctx.send("The prefix cannot be more than 5 characters.")
        else:
            if db.record("SELECT * FROM guilds WHERE GuildID = ?", ctx.guild.id):
                db.execute("UPDATE guilds SET Prefix = ? WHERE GuildID = ?", new, ctx.guild.id)
            else:
                db.execute("INSERT INTO guilds(GuildID, Prefix) VALUES (?,?)", ctx.guild.id, new)
                # await ctx.send("Server newly registered, must restart bot or re-invite.")
            await ctx.send(f"Prefix set to {new}.")

    @change_prefix.error
    async def change_prefix_error(self, ctx, exc):
        if isinstance(exc, CheckFailure):
            await ctx.send("You need the Manage Server permission to do that.")

    @command(brief="Clears a specified number of messages.")
    @has_permissions(manage_messages=True)
    async def clear(self, ctx, amount=1):
        if amount > 10:
            return await ctx.send("Too much amount to delete.")
        await ctx.channel.purge(limit=amount + 1)

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("You do not have permission for managing messages.")

    @command()
    async def water(self, ctx):
        if not (water_role := get(ctx.guild.roles, name="water-ping")):
            water_role = await ctx.guild.create_role(name="water-ping", color=Color.from_rgb(0, 204, 255))
        await ctx.author.add_roles(water_role)
        await ctx.message.add_reaction("\N{THUMBS UP SIGN}")

    async def water_ping(self):
        a_channels = dict(db.records("SELECT GuildID, announcementChannelID "
                                     "FROM guilds WHERE announcementChannelID IS NOT NULL"))
        for guildID in a_channels:
            guild = self.bot.get_guild(guildID)
            if water_role := get(guild.roles, name="water-ping"):
                if water_role.members:
                    channel = self.bot.get_channel(a_channels[guildID])
                    await channel.send(f"{water_role.mention}")


def setup(bot):
    dis_bot = Misc(bot)
    bot.add_cog(dis_bot)
    bot.scheduler.add_job(dis_bot.water_ping, CronTrigger(minute=0, second=0))
