import discord
from discord.ext import commands
from datetime import datetime as dt
from datetime import timedelta

max = 160  # max resins
rate = 8  # 1 resin per 8 mins


class Genshin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def resin(self, ctx, resin_count, *args):
        try:
            resin_count = int(resin_count)
            args = [int(a) for a in args]
        except ValueError:
            await ctx.send("Input integer only for <resin_count> and <resin-stops>.")

        if resin_count > max:
            return await ctx.send(f"<resin_count> is beyond max resins ({max}).")

        answers = []
        for stop in args:
            if (diff := stop - resin_count) >= 0:
                mins_left = timedelta(minutes=diff * rate)
                answer = dt.now() + mins_left
                answers.append(f"{stop} resins at {answer.strftime('%I:%M %p')}\n")
            else:
                answers.append(f"Already beyond {stop} resins.\n")

        desc = ""
        for a in answers:
            desc += a
        embed = discord.Embed(description=desc)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Genshin(bot))
