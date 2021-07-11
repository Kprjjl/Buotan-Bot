import discord
import re
import asyncio
from discord.ext import commands, tasks
import datetime as dt

# ex: "25-5-15 (0/4) w || 25m 0s" OR "50-10 b || 50m 0s"
# format: "<work time>-<short break>-<interval break> (<interval progress>/<max interval>) <state> || <mins>m 0s
# <mins> must be divisible by 5
# <state> values: "w" for work, "b" for short break, "B" for interval break
pomo_channel_regex = ["^(\d+)-(\d+)-(\d+) \((\d+)\/(\d+)\) (w|b|B) \|{2} (\d+)m 0s$",
                      "^(\d+)-(\d+) (w|b) \|{2} (\d+)m 0s$"]
# regex matches would be size 7 or 4
alarm_ring_file = "./audio/alarm_classic.mp3"


class PomoGuild:
    def __init__(self, guild):
        self.guild = guild
        self.first_time = True

    def __repr__(self):
        return f"Guild: {self.guild.name} | first_time: {self.first_time}"


class PomoConfig:
    def __init__(self, ch_name):
        configs, self.size = self.get_configs(ch_name)

        if self.size == 7:
            # state_position = 5
            self.worktime, self.shortbreak, self.longbreak, self.numpomo, self.maxpomo, \
                self.state, self.timeleft = configs
        elif self.size == 4:
            # state_position = 2
            self.worktime, self.shortbreak, \
                self.state, self.timeleft = configs

    def proceed(self):  # return True if there is state change, False otherwise
        self.timeleft -= 5
        if self.timeleft == 0:
            if self.state == 'w':
                if self.size == 7:
                    self.numpomo += 1
                    if self.numpomo < self.maxpomo:
                        self.timeleft = self.shortbreak  # start shortbreak
                        self.state = 'b'
                    else:
                        self.numpomo = 0
                        self.timeleft = self.longbreak  # start longbreak
                        self.state = 'B'
                elif self.size == 4:
                    self.timeleft = self.shortbreak  # start shortbreak
                    self.state = 'b'
            elif self.state in ['b', 'B']:
                self.timeleft = self.worktime  # start worktime
                self.state = 'w'
            return True
        return False

    def to_string(self):
        # New name construction (size == 7 ex: "25-5-15 (2/4) b || 5m 0s")
        new_name = f"{self.worktime}-{self.shortbreak}"  # "25-5"
        if self.size == 7:
            new_name += f"-{self.longbreak} ({self.numpomo}/{self.maxpomo})"  # "-15 (2/4)"
        new_name += f" {self.state} || {self.timeleft}m 0s"  # " b || 5m 0s"
        return new_name

    @staticmethod
    def get_configs(ch_name):  # returns (list, int)
        if configs := re.findall(pomo_channel_regex[0], ch_name):
            configs = configs[0]
            size = 7
            state_position = 5
        elif configs := re.findall(pomo_channel_regex[1], ch_name):
            configs = configs[0]
            size = 4
            state_position = 2
            if configs[2] == 'B':
                raise ValueError  # size 4 configs do not include a long break state
        else:
            raise ValueError  # wrong format
        configs = [int(configs[i]) if i != state_position else configs[i] for i in range(size)]

        # time numbers should be divisible by 5
        if size == 7:
            for i in range(size):
                if i in [3, 4, 5]:  # exclude <interval progress>,<max interval>,<state>
                    continue
                elif configs[i] % 5 == 0:
                    continue
                raise ValueError
        elif size == 4:
            for i in range(size):
                if i == 2:  # exclude <state>
                    continue
                elif configs[i] % 5 == 0:
                    continue
                raise ValueError

        # <mins> should be less than or equal to corresponding time setting depending on <state>
        if configs[-2] == 'w':
            if configs[-1] > configs[0]:  # if <timeleft> > <work time>
                raise ValueError
        elif configs[-2] == 'b':
            if configs[-1] > configs[1]:  # <short break>
                raise ValueError
        elif configs[-2] == 'B':
            if configs[-1] > configs[2]:  # <long break>
                raise ValueError
        else:
            raise ValueError  # incase

        return configs, size

    def __repr__(self):
        return self.to_string()


class Study(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.ongoing = []  # list of qualified guilds that invoked .startpomos

        self.remind_list = {}
        self.objective_ch = {}

        self.water_ch = {}

    # -------- pomodoro stuff ----------
    @tasks.loop(minutes=5)
    async def update_pomos(self):
        print("----------------------")
        print(dt.datetime.now())
        to_delete = []
        for pomoguild in self.ongoing:
            if not (pomo_ctg := discord.utils.get(pomoguild.guild.categories, name="POMODOROS")):
                to_delete.append(pomoguild)
                continue

            pomo_channels = pomo_ctg.channels
            for ch in pomo_channels:
                try:
                    cfg = PomoConfig(ch.name)
                    print(ch.name, end=" --> ")
                except ValueError:
                    continue
                else:
                    if pomoguild.first_time:
                        cfg.timeleft += 5  # to offset when starting for the first time from startpomos()
                    if cfg.timeleft > 0:
                        if cfg.proceed():
                            if ch.members:
                                await asyncio.sleep(.5)
                                vclient = await ch.connect()
                                vclient.play(discord.FFmpegPCMAudio(alarm_ring_file))
                                while True:
                                    await asyncio.sleep(.5)
                                    if not vclient.is_playing():
                                        await vclient.disconnect()
                                        break

                    await ch.edit(name=cfg.to_string())
                    print(cfg.to_string())
                await asyncio.sleep(.5)

            if pomoguild.first_time:
                pomoguild.first_time = False
            await asyncio.sleep(.5)

        for guild in to_delete:
            del self.ongoing[guild]

    @commands.command()
    async def startpomos(self, ctx):
        """
        Registers pomodoro channels under 'POMODORO' category and starts their timers.
        ```
        Pomodoro Voice Channel Name Format:
        <worktime>-<shortbreak>[-<longbreak> (<# of pomodoros>/<max # of pomodoros>)] <state> || <timeleft>m 0s
        ```
        Examples of Valid Pomodoro Voice Channel Names:
        w/ long breaks: `25-5-15 (0/4) w || 25m 0s`
        w/o long breaks: `50-10 w || 50m 0s`
        """
        if ctx.guild in self.ongoing:
            return await ctx.send("Study sessions have already started.")
        else:
            self.ongoing.append(PomoGuild(ctx.guild))
            if not self.update_pomos.is_running():
                self.update_pomos.start()
            await ctx.send("Pomodoros Started")

    @commands.command()
    async def restartpomos(self, ctx):
        """Resets the bot's list of registered pomodoro channels and calls `startpomos` command"""
        await self.stoppomos(ctx)
        await self.startpomos(ctx)

    @commands.command()
    async def stoppomos(self, ctx):
        """Stops timers of pomodoro channels"""
        try:
            for pomoguild in self.ongoing:
                if pomoguild.guild == ctx.guild:
                    self.ongoing.remove(ctx.guild)
        except ValueError:
            await ctx.send("Timers are already stopped.")
        else:
            await ctx.send("Pomodoro timers have been stopped.")
    # ---------------------------

    # ---------- mini reminder ----------
    @commands.command(name="init_ob_ch")
    async def init_objective_ch(self, ctx):
        """Registers text channel where the bot will remind objectives of `objective` command users."""
        self.objective_ch[ctx.guild] = ctx.channel
        await ctx.send(f"Objectives channel set to `{ctx.channel.name}`")

    @commands.command()
    async def objective(self, ctx, *, arg):
        """
        Registers one objective that the user is expected to finish.
        <arg> Syntax:
        `<objective name>` >> `<hours>hr`, `<minutes>m`
        Example:
            `.objective doing tasks >> 1hr 30m`
        """
        if not self.objective_ch.get(ctx.guild):
            return await ctx.send(f"Please use `init_ob_ch` command to set objective channel")
        try:
            obj, *time = re.findall("([\w\W]+)>>\s*(\d+(hrs?|m|h))[,\s]*(\d+(hrs?|m|h))?", arg)[0]
        except IndexError:
            await ctx.send("Follow .objective `objective` >> `#hr`, `#m` format.")
        except ValueError:
            await ctx.send("Follow .objective `objective` >> `#hr`, `#m` format.")
        except Exception as e:
            print(e)
        else:
            time = [t for t in time if t]
            obj = obj.strip()
            time_d = {}

            time = (t for t in time)
            prev = next(time)
            while True:
                try:
                    current = next(time)
                except StopIteration:
                    break
                if current in ['hrs', 'hr', 'h', 'm']:
                    if current == 'hrs' or current == 'hr':
                        current = 'h'
                    time_d[current] = int(prev[:-1])
                else:
                    prev = current

            self.remind_list[(self.objective_ch[ctx.guild], ctx.author)] = (obj, time_d, dt.datetime.now())
            if not self.remind_objective.is_running():
                self.remind_objective.start()
            await ctx.send(f"{ctx.author.mention} has listed an objective of `{obj}`.")

    @tasks.loop(minutes=1)
    async def remind_objective(self):
        to_delete = []
        for channel, member in self.remind_list:
            hours = self.remind_list[(channel, member)][1].get('h', 0)
            minutes = self.remind_list[(channel, member)][1].get('m', 0)
            if dt.datetime.now() - self.remind_list[(channel, member)][2] >= dt.timedelta(hours=hours, minutes=minutes):
                await channel.send(f"{member.mention}, it has been `{hours}h, {minutes}m` since "
                                   f"you listed your objective: `{self.remind_list[(channel, member)][0]}`")
        for key in to_delete:
            del self.remind_list[key]

        if not self.remind_list:
            return self.remind_objective.cancel()
    # -----------------------------------

    @commands.command()
    async def init_h20_ch(self, ctx):
        """Registers text channel where the bot will remind members to hydrate themselves."""
        self.water_ch[ctx.guild] = ctx.channel
        await ctx.send(f"Water ping channel set to `{ctx.channel.name}`")

    @commands.command()
    async def water(self, ctx):
        """
        Gives `water-ping` role.
        Starts reminding `water-ping` members to hydrate themselves every ~1 hour.
        """
        if not (water_role := discord.utils.get(ctx.guild.roles, name="water-ping")):
            water_role = await ctx.guild.create_role(name="water-ping", color=discord.Color.from_rgb(0, 204, 255))
        await ctx.author.add_roles(water_role)
        if not self.water_ping.is_running():
            self.water_ping.start()

    @tasks.loop(hours=1)
    async def water_ping(self):
        for guild in self.water_ch:
            if water_role := discord.utils.get(guild.roles, name="water-ping"):
                if not water_role.members:
                    await self.water_ch[guild].send(f"{water_role.mention}")

    @commands.command(aliases=["ongoing"])
    @commands.is_owner()
    async def ongoing_pomos(self, ctx):
        print("------------------------------")
        print(dt.datetime.now())
        for pomoguild in self.ongoing:
            print(pomoguild)
        if self.update_pomos.is_running():
            print("update_pomos is running.")
        else:
            print("update_pomos is NOT running.")
        if self.water_ping.is_running():
            print("water_ping is running.")
        else:
            print("water_ping is NOT running.")
        if self.remind_objective.is_running():
            print("remind_objective is running.")
        else:
            print("remind_objective is NOT running.")
        print("------------------------------")

    def cog_unload(self):
        print("Unloading Study cog.")
        self.update_pomos.cancel()
        self.water_ping.cancel()
        self.remind_objective.cancel()
        print("Study cog loops cancelled.")


def setup(bot):
    bot.add_cog(Study(bot))
