import discord
import re
import asyncio
from discord.ext import commands, tasks

# ex: "25-5-15 (0/4) w || 25m 0s" OR "50-10 b || 50m 0s"
# format: "<work time>-<short break>-<interval break> (<interval progress>/<max interval>) <state> || <mins>m 0s
# <mins> must be divisible by 5
# <state> values: "w" for work, "b" for short break, "B" for interval break
pomo_channel_regex = ["^(\d+)-(\d+)-(\d+) \((\d+)\/(\d+)\) (w|b|B) \|{2} (\d+)m 0s$",
                      "^(\d+)-(\d+) (w|b) \|{2} (\d+)m 0s$"]
# regex matches would be size 7 or 4


class Study(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.ongoing = []
        self.pomo_ctg = None
        self.pomo_channels = []

        self.remind_list = {}

    # -------- pomodoro stuff ----------
    @staticmethod
    def pomo_configs(name):  # returns (list, int) or False
        if configs := re.findall(pomo_channel_regex[0], name):
            configs = configs[0]
            configs = [int(configs[i]) if i != 5 else configs[i] for i in range(7)]
            size = 7
        elif configs := re.findall(pomo_channel_regex[1], name):
            configs = configs[0]
            configs = [int(configs[i]) if i != 2 else configs[i] for i in range(4)]
            if configs[-2] == 'B':
                return False    # size 4 configs do not include long breaks
            size = 4
        else:
            return False

        # time numbers should be divisible by 5
        if size == 7:
            for i in range(size):
                if i in [3, 4, 5]:  # exclude <interval progress>,<max interval>,<state>
                    continue
                elif configs[i] % 5 == 0:
                    continue
                return False
        elif size == 4:
            for i in range(size):
                if i == 2:  # exclude <state>
                    continue
                elif configs[i] % 5 == 0:
                    continue
                return False

        # <mins> should be less than or equal to corresponding time setting depending on <state>
        if configs[-2] == 'w':
            if configs[-1] <= configs[0]:   # <work time>
                return configs, size
        elif configs[-2] == 'b':
            if configs[-1] <= configs[1]:   # <short break>
                return configs, size
        elif configs[-2] == 'B':
            if configs[-1] <= configs[2]:   # <long break>
                return configs, size
        else:
            return False

        return False    # channel does not fit the criteria

    @tasks.loop(minutes=5)
    async def pomo_update(self):
        test_ch = discord.utils.get(self.pomo_ctg.channels, id=858860911313158174)
        await test_ch.send("5 mins have passed.")
        for ch in self.pomo_channels:
            if cfg := self.pomo_configs(ch.name):
                size = cfg[1]
                cfg = cfg[0]

                cfg = list(cfg)
                if ch not in self.ongoing:
                    cfg[-1] += 5  # to offset
                    self.ongoing.append(ch)
                if ch in self.ongoing and cfg[-1] > 0:
                    cfg[-1] -= 5  # decrease <mins> by 5

                # change state when <mins> is zero
                if cfg[-1] == 0:
                    if cfg[-2] == 'w':
                        if size == 7:  # <work-time> can go to either <short-break> or <long-break>
                            cfg[3] += 1  # completed one pomodoro
                            if cfg[3] < cfg[4]:
                                cfg[-1], cfg[-2] = cfg[1], 'b'
                            else:  # cfg[3] == cfg[4] || <interval progress> == <max interval>
                                cfg[3] = 0  # reset
                                cfg[-1], cfg[-2] = cfg[2], 'B'  # start long break
                        elif size == 4:
                            cfg[-1], cfg[-2] = (cfg[1], 'b')
                    elif cfg[-2] == 'b' or cfg[-2] == 'B':
                        cfg[-1], cfg[-2] = (cfg[0], 'w')

                # New name construction (size == 7 ex: "25-5-15 (2/4) 'b' || 5m 0s")
                new_name = f"{cfg[0]}-{cfg[1]}"  # "25-5"
                if size == 7:
                    new_name += f"-{cfg[2]} ({cfg[3]}/{cfg[4]})"  # "-15 (2/4)"
                new_name += f" {cfg[-2]} || {cfg[-1]}m 0s"  # " || 5m 0s"

                await ch.edit(name=new_name)
                await asyncio.sleep(1)

    @commands.command()
    async def startpomos(self, ctx):
        if self.ongoing:
            return await ctx.send("Study sessions have already started.")
        else:
            if self.pomo_update.is_running():  # for restarting
                self.pomo_update.cancel()

            self.pomo_ctg = discord.utils.get(ctx.guild.categories, name="POMODOROS")
            if self.pomo_ctg is None:
                return await ctx.send("No category channel named 'POMODOROS' found.")

            for c in self.pomo_ctg.channels:
                if self.pomo_configs(c.name):
                    self.pomo_channels.append(c)

            # start loop
            self.pomo_update.start()
            await ctx.send("Pomodoros Started")

    @commands.command()
    async def restartpomos(self, ctx):
        self.ongoing = []
        self.pomo_channels = []
        await self.startpomos()

    @commands.command()
    async def stoppomos(self, ctx):
        if self.pomo_update.is_running():
            self.pomo_update.cancel()
            await ctx.send("Pomodoro timers have been cancelled.")
        else:
            await ctx.send("Timers are already stopped.")
    # ---------------------------

    # ---------- mini reminder ----------
    @commands.command()
    async def objective(self, ctx, *, obj):
        pass


def setup(bot):
    bot.add_cog(Study(bot))
