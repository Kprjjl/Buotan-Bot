import os
from discord.ext import commands

with open('token', 'r') as tf:
    line = tf.readline()
    token = line.rstrip()


def get_prefix(bot, message):
    with open('prefix', 'r') as pf:
        try:
            line1 = pf.readline()
        except IOError:
            PREFIX = '!'
            print("Error getting prefix from prefix.txt; Used '!' instead.")
        else:
            PREFIX = line1.strip()
    return PREFIX


bot = commands.Bot(command_prefix=get_prefix)

for file_name in os.listdir('./cogs'):
    if file_name.endswith('.py'):
        bot.load_extension(f'cogs.{file_name[:-3]}')
        print(f'Loaded {file_name}')


def main(name):
    @bot.event
    async def on_ready():
        print("Bot is ready.")

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Invalid Command:\n{error}")

    @bot.command()
    async def ping(ctx):
        await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

    @bot.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(ctx, amount=1):
        await ctx.channel.purge(limit=amount + 1)

    @clear.error
    async def clear_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission for managing messages.")

    bot.run(token)


if __name__ == '__main__':
    main('PyCharm')
