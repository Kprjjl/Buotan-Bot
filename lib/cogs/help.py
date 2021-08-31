from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.utils import get
from discord import Embed
from typing import Optional
from discord.ext.menus import MenuPages, ListPageSource


def syntax(cmd):
    cmd_and_aliases = "|".join([str(cmd), *cmd.aliases])
    params = []
    for key, value in cmd.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "NoneType" in str(value) else f"<{key}>")
    params = " ".join(params)
    return f"```{cmd_and_aliases} {params}```"


class HelpMenu(ListPageSource):
    def __init__(self, ctx, data):
        data = [d for d in data if not d.hidden]
        self.ctx = ctx
        super().__init__(data, per_page=3)

    async def write_page(self, menu, fields=None):
        if fields is None:
            fields = []
        offset = (menu.current_page*self.per_page) + 1
        len_data = len(self.entries)
        embed = Embed(title="Help",
                      description="Welcome to help dialog.",
                      color=self.ctx.author.color)
        embed.set_footer(
            text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} commands.")

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)
        return embed

    async def format_page(self, menu, entries):
        fields = []
        for entry in entries:
            fields.append((entry.brief or "No description", syntax(entry)))

        return await self.write_page(menu, fields)


class Help(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")

    @staticmethod
    async def cmd_help(ctx, cmd):
        embed = Embed(title=f"Help with `{cmd}`",
                      description=syntax(cmd),
                      color=ctx.author.color)
        embed.add_field(name="Command description", value=cmd.help)
        await ctx.send(embed=embed)

    @command(name="help",
             brief="Opens help dialog or provides specific help on a command.")
    async def show_help(self, ctx, cmd: Optional[str]):
        if cmd is None:
            menu = MenuPages(source=HelpMenu(ctx, list(self.bot.commands)),
                             delete_message_after=True, timeout=60.0)
            await menu.start(ctx)
        else:
            if cmd := get(self.bot.commands, name=cmd, hidden=False):
                await self.cmd_help(ctx, cmd)
            else:
                await ctx.send("That command does not exist.")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("help")


def setup(bot):
    bot.add_cog(Help(bot))
