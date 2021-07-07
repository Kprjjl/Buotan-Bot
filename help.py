import discord
from discord.ext import commands


def syntax(command):
    cmd_and_aliases = "|".join([str(command), *command.aliases])

    params = []
    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "NoneType" in str(value) else f"<{key}>")
    params = " ".join(params)

    return f"```{cmd_and_aliases} {params}```"


class Help(commands.HelpCommand):
    def __init__(self):
        super().__init__()

    async def send_bot_help(self, mapping):
        embed = discord.Embed(description="Commands for this bot.\n"
                                          "`help [command]` for specific command help.")
        for cog in mapping:
            cmds = '`, `'.join([command.name for command in mapping[cog]])
            cmds = f"`{cmds}`"
            if cog is not None:
                cog_name = cog.qualified_name
                if cog_name == "OwnerCommands":
                    continue
            else:
                cog_name = "General"
            embed.add_field(name=cog_name, value=cmds, inline=False)
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Help with `{command}`",
                              description=syntax(command))
        embed.add_field(name="Command description", value=command.help)
        await self.get_destination().send(embed=embed)

    # async def send_cog_help(self, cog):
    #     return await super().send_cog_help(cog)
    # async def send_group_help(self, group):
    #     return await super().send_group_help(group)
