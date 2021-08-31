from discord.ext.commands import Cog, command


class Pomodoro(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("pomodoro")


def setup(bot):
    dis_bot = Pomodoro(bot)
    bot.add_cog(dis_bot)

