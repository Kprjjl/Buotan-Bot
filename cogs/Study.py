import discord
import re
from discord.ext import commands, tasks

# ex: "25-5-15 (1/4) w || 25m 0s" OR "50-10 b || 50m 0s"
# format: "<work time>-<short break>-<interval break> (<interval progress>/<max interval>) <state> || <mins>m 0s
# <mins> must be divisible by 5
# <state> values: "w" for work, "b" for short break, "B" for interval break
# pomo_channel_regex = "^(\d+)-(\d+)(-\d+ \(\d+\/\d+\))? (w|b|B) \|{2} (\d+)m 0s$"
pomo_channel_regex1 = "^(\d+)-(\d+)-(\d+) \((\d+)\/(\d+)\) (w|b|B) \|{2} (\d+)m 0s$"
pomo_channel_regex2 = "^(\d+)-(\d+) (w|b) \|{2} (\d+)m 0s$"
# regex matches would be size 7 or 4


class Study(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ongoing = False
        self.pomo_ctg = None
        self.pomo_channels = None

    @tasks.loop(minutes=5)
    async def pomo_update(self):
        for ch in self.pomo_channels:
            size = len(ch)
            pass

    @commands.command()
    async def startstudy(self, ctx):
        if self.ongoing is True:
            return await ctx.send("Study sessions have already started.")
        else:
            self.pomo_ctg = discord.utils.get(ctx.guild.categories, name="POMODOROS")
            if self.pomo_ctg is None:
                return await ctx.send("No category channel named 'POMODOROS' found.")

            # get all pomodoro channels (channels under POMODORO category)
            def is_pomo_channel(ch):
                # 1. must match to regex
                y = re.findall(pomo_channel_regex1, ch.name)
                if not y:  # if y == []:
                    if not (y := re.findall(pomo_channel_regex2, ch.name)):
                        return False
                # 2. all time numbers must be divisible by 5
                size = len(y)
                if size == 7:
                    for i in range(size):
                        if i in [3, 4, 5]:  # exclude <interval progress>,<max interval>,<state>
                            continue
                        elif int(y[i]) % 5 == 0:
                            continue
                        return False
                elif size == 4:
                    for i in range(size):
                        if i == 2:  # exclude <state>
                            continue
                        elif int(y[i]) % 5 == 0:
                            continue
                        return False
                return True
            self.pomo_channels = [c for c in self.pomo_ctg.channels if is_pomo_channel(c)]

            # start loop
            self.pomo_update.start()
            await ctx.send("Pomodoros Started")
            self.ongoing = True

    @commands.command()
    async def restartstudy(self, ctx):
        pass


def setup(bot):
    bot.add_cog(Study(bot))
