from discord import Intents
from glob import glob
from discord.ext.commands import Bot as BotBase
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext.commands import Context
from discord.ext.commands import (CommandNotFound, BadArgument, MissingRequiredArgument)
from discord.ext.commands import when_mentioned_or
from discord.errors import HTTPException, Forbidden
from ..db import db
from asyncio import sleep

OWNER_IDS = [454214749245276160]
COGS = [path.split("\\")[-1][:-3] for path in glob("./lib/cogs/*.py")]
IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument)


def get_prefix(bot, message):
    prefix = db.field("SELECT Prefix FROM guilds WHERE GuildID = ?", message.guild.id)
    try:
        return when_mentioned_or(prefix)(bot, message)
    except Exception as e:
        print(prefix, type(prefix))
        raise e


class Ready(object):
    def __init__(self):
        for cog in COGS:
            setattr(self, cog, False)

    def ready_up(self, cog):
        setattr(self, cog, True)
        print(f"{cog} cog ready")

    def all_ready(self):
        return all([getattr(self, cog) for cog in COGS])


class Bot(BotBase):
    def __init__(self):
        self.VERSION = None
        self.TOKEN = None
        self.ready = False
        self.cogs_ready = Ready()
        self.guild = None
        self.scheduler = AsyncIOScheduler()
        db.autosave(self.scheduler)

        super().__init__(
            command_prefix=get_prefix,
            owner_ids=OWNER_IDS,
            intents=Intents.all()
        )

    def setup(self):
        for cog in COGS:
            self.load_extension(f"lib.cogs.{cog}")
            print(f"{cog} cog loaded.")

        print("setup complete.\n-----------------")

    def run(self, version):
        self.VERSION = version
        print("running setup...")
        self.setup()

        with open("./lib/bot/token", "r", encoding="utf-8") as tf:
            self.TOKEN = tf.read()
        super().run(self.TOKEN, reconnect=True)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is not None and ctx.guild is not None:
            if self.ready:
                await self.invoke(ctx)
            else:
                await ctx.send("I'm not yet ready to receive commands. Please wait a few seconds.")

    @staticmethod
    async def on_connect():
        print("Bot connected.")

    @staticmethod
    async def on_disconnect():
        print("Bot disconnected.")

    async def on_error(self, event_method, *args, **kwargs):
        if event_method == "on_command_error":
            await args[0].send("Something went wrong.")

        print("An error occurred.")
        raise

    async def on_command_error(self, context, exception):
        if any([isinstance(exception, error) for error in IGNORE_EXCEPTIONS]):
            pass
        elif isinstance(exception, MissingRequiredArgument):
            await context.send("One or more required arguments are missing.")
        elif hasattr(exception, "original"):
            if isinstance(exception.original, HTTPException):
                return await context.send("Unable to send message.")
            if isinstance(exception.original, Forbidden):
                return await context.send("I do not have permission to do that.")
            raise exception.original
        else:
            raise exception

    async def on_ready(self):
        if not self.ready:
            self.guild = self.get_guild(879912501679108116)
            self.scheduler.start()
            # channel = self.get_channel(751762510398488606)
            # await channel.send("Now online.")

            while not self.cogs_ready.all_ready():
                await sleep(0.5)

            self.ready = True
            print("Bot ready.\n-----------------")
        else:
            print("Bot reconnected.")

    async def on_message(self, message):
        # if message.author.bot and message.author != message.guild.me:
        if not message.author.bot:
            await self.process_commands(message)


bot = Bot()


@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")


@bot.event
async def on_guild_join(guild):
    db.execute("INSERT INTO guilds(GuildID) VALUES (?)", guild.id)


@bot.event
async def on_guild_remove(guild):
    db.execute("DELETE FROM guilds WHERE GuildID = ?", guild.id)
