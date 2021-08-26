import discord
from peewee import IntegrityError
from discord.ext import commands, tasks
from models.sched_models import *
from datetime import datetime as dt
from datetime import time

frequencies = {
    1: ({'sunday', 'sun', '1'}, 'Sunday'),
    2: ({'monday', 'mon', '2'}, 'Monday'),
    3: ({'tuesday', 'tue', '3'}, 'Tuesday'),
    4: ({'wednesday', 'wed', '4'}, 'Wednesday'),
    5: ({'thursday', 'thu', '5'}, 'Thursday'),
    6: ({'friday', 'fri', '6'}, 'Friday'),
    7: ({'saturday', 'sat', '7'}, 'Saturday'),
    8: ({'once', 'o', '8'}, 'Once')
}


class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if db.connect():
            print("connected to Scheduler db.")

    def cog_unload(self):
        db.close()
        print("Scheduler db closed.")

    @commands.command(aliases=['init_a_chnl'])
    async def init_announce_chnl(self, ctx: discord.ext.commands.Context):
        query = AnnouncementChannel.select().where(AnnouncementChannel.guild_id == ctx.guild.id).first()
        if query is None:
            a_channel = AnnouncementChannel.create(guild_id=ctx.guild.id, discord_id=ctx.channel.id)
            a_channel.save()
        else:
            query.discord_id = ctx.channel.id
            query.save()
        return await ctx.send(f"Announcement channel for this server set to: {ctx.channel.mention}")

    @staticmethod
    def fmt_datetime(s, formats: tuple):
        formats = (f for f in formats)
        index = 0
        while True:
            try:
                f = next(formats)
                if index != 1:
                    s = dt.strptime(s, f)
                else:
                    s = dt.strptime(s, f).replace(year=dt.now().year)
            except ValueError:
                index += 1
                continue
            except StopIteration:
                return False
            else:
                break
        return s

    @commands.command()
    async def addevent(self, ctx, title, start=None, end=None, dates=None, freq="once", *, desc=None):
        freq = freq.lower()
        if freq not in frequencies[8][0]:
            freq_gen = (f for f in frequencies.values())
            while True:
                try:
                    f = next(freq_gen)
                    if freq in f[0]:
                        freq = f[1]
                        break
                except StopIteration:
                    desc = freq + str(desc)
                    freq = "Once"
        else:
            freq = "Once"
        freq = Frequency.select().where(Frequency.freq == freq).get()

        none_equivs = {'', 'na', 'n/a', '.', None}
        time_fmt = ("%I:%M%p", "%I%p")
        date_fmt = ("%d-%m-%y", "%d-%m")
        now = dt.now()

        if start in none_equivs:
            start = now.time()
        else:
            start = Scheduler.fmt_datetime(start, time_fmt)
            if not start:
                return await ctx.send("Improper `start` input.")
            else:
                start = start.time()

        if end in none_equivs:
            end = time(23, 59, 59)
        else:
            end = Scheduler.fmt_datetime(end, time_fmt)
            if not end:
                return await ctx.send("Improper `end` input.")
            else:
                end = end.time()

        if dates and dates not in none_equivs:
            try:
                if s_date := Scheduler.fmt_datetime(dates, date_fmt):
                    s_date = s_date.date()
                    e_date = s_date
                else:
                    s_date, e_date = dates.split("//")
                    if s_date in none_equivs:  # //<end-date> not allowed
                        raise ValueError
                    if s_date := Scheduler.fmt_datetime(s_date, date_fmt):
                        s_date = s_date.date()

                    temp_var = e_date
                    if e_date := Scheduler.fmt_datetime(e_date, date_fmt):
                        e_date = e_date.date()
                    else:
                        if temp_var in none_equivs:
                            e_date = s_date
                        else:
                            raise ValueError
            except ValueError:
                return await ctx.send("Improper `dates` input")
        else:
            s_date = now.date()
            e_date = s_date

        start = dt.combine(s_date, start)
        end = dt.combine(e_date, end)
        if start < end:
            event = Event.create(
                title=title,
                start=start,
                end=end,
                freq_id=freq,
                desc=desc
            )
            return await ctx.send(f"New Event added with :id: `{event.id}`")
        else:
            return await ctx.send(f"start time must be earlier than end time.")

    @commands.command()
    async def del_event(self, ctx, event_id):
        try:
            event = Event.select().where(Event.id == int(event_id)).get()
            title = event.title
        except pw.DoesNotExist:
            return await ctx.send(f"Event with :id: `{event_id}` does not exist.")
        except ValueError:
            return await ctx.send("Improper `event_id` input.")
        else:
            participants = event.involved
            if participants.exists():
                event.delete_instance(recursive=True)
                for participant in participants:
                    if not hasattr(participant, 'events'):
                        participant.delete_instance()
            else:
                event.delete_instance(recursive=True)
            return await ctx.send(f"Event: `{title}` deleted.")

    @commands.command()
    async def events(self, ctx):
        desc = ""
        for event in Event.select():
            desc += f":id: `{event.id}` | **{event.title}**\n" \
                # f"------- `{event.start.strftime('%d-%m-%y')} - {event.end.strftime('%d-%m-%y')}`\n" \
            # f"-------- `{event.start.strftime('%I:%M%p')} - {event.end.strftime('%I:%M%p')}`\n"
        embed = discord.Embed(title="Registered Events:", description=desc)
        return await ctx.send(embed=embed)

    @commands.command()
    async def participate(self, ctx, event_id, *, args=None):
        if args is None:
            participants = [ctx.author]
        else:
            participants = ctx.message.mentions + ctx.message.role_mentions
        # get event
        try:
            query = Event.select().where(Event.id == int(event_id)).get()
        except ValueError:
            return await ctx.send("Improper `event_id` input.")
        except pw.DoesNotExist:
            return await ctx.send(f"Event with :id: `{event_id}` does not exist.")
        else:
            event = query

        # create Participant and Involvement
        for participant in participants:
            discord_id = participant.id
            try:
                participant = Participant.create(
                    discord_id=discord_id, mention=participant.mention, name=participant.name)
            except IntegrityError:
                participant = Participant.select().where(Participant.discord_id == discord_id).get()

            try:
                Involvement.create(participant_id=participant, event_id=event)
            except IntegrityError:
                continue
        return await ctx.send(f"Participation registered.")

    @commands.command()
    async def remove_participation(self, ctx, event_id, *, args=None):
        if args is None:
            participants = [ctx.author]
        else:
            participants = ctx.message.mentions + ctx.message.role_mentions

        try:
            query = Event.select().where(Event.id == int(event_id))
        except ValueError:
            return await ctx.send("Improper `event_id` input.")
        else:
            if query.exists():
                event = query.get()
            else:
                return await ctx.send(f"Event with :id: `{event_id}` does not exist.")

        for participant in participants:
            try:
                involvement = Involvement.select().where(
                    Involvement.participant_id == participant.id & Involvement.event_id == event.id
                ).get()
            except pw.DoesNotExist:
                continue
            else:
                involvement.delete_instance()

            participant = Participant.select().where(Participant.discord_id == participant.id).get()
            if participant.events.exists():
                continue
            else:
                participant.delete_instance()
        return await ctx.message.add_reaction("\N{THUMBS UP SIGN}")

    @commands.command()
    async def event(self, ctx, event_id):
        try:
            event = Event.select().where(Event.id == int(event_id)).get()
        except pw.DoesNotExist:
            return await ctx.send(f"Event with :id: `{event_id}` does not exist.")
        except ValueError:
            return await ctx.send("Improper `event_id` input.")
        else:
            query = Participant.select().join(Involvement).join(Event).where(Event.id == event.id)
            if query.exists():
                value = ""
                for participant in query:
                    value += f"`@{participant.name}`, "
                value = value[:-2]
            else:
                value = "None"
            desc = f"start: `{event.start.strftime('%I:%M%p %d-%m-%y %a')}`\n" \
                   f"end: `{event.end.strftime('%I:%M%p %d-%m-%y %a')}`\n" \
                   f"repeats: `{event.freq_id.freq}`"
            embed = discord.Embed(title=f"{event.title} | :id: `{event.id}`", description=desc)
            embed.add_field(inline=False,
                            name="----------- Participants: -----------",
                            value=value)
            return await ctx.send(embed=embed)

    @commands.command()
    async def ping_event(self, ctx, event_id):
        try:
            event = Event.select().where(Event.id == int(event_id)).get()
        except pw.DoesNotExist:
            return await ctx.send(f"Event with :id: `{event_id}` does not exist.")
        except ValueError:
            return await ctx.send("Improper `event_id` input.")
        else:
            query = Participant.select().join(Involvement).join(Event).where(Event.id == event.id)
            if query.exists():
                message = f"Pinged for event: **{event.title}**\n"
                for participant in query:
                    message += f"{participant.mention}, "
                message = message[:-2]
            else:
                message = "No participants for that event."
            return await ctx.send(message)

    @commands.command(name="checkschedule", aliases=['checksched'])
    async def check_schedule(self, ctx):
        now = dt.now()
        query = Event.select().where(Event.start <= now <= Event.end)
        desc = ""
        for event in query:
            desc += f":id: `{event.id}` | **{event.title}**\n" \
                    f"------- `{event.start.strftime('%d-%m-%y')} - {event.end.strftime('%d-%m-%y')}`\n" \
                    f"-------- `{event.start.strftime('%I:%M%p')} - {event.end.strftime('%I:%M%p')}`\n"
        embed = discord.Embed(title="Ongoing events:", description=desc)
        return await ctx.send(embed=embed)

    # @tasks.loop(minutes=1)
    # async def update_events(self):
    #     now = dt.now()
    #     channels = AnnouncementChannel.select()
    #     for a_channel in channels:
    #         query = Event.select()
    #         for event in query:
    #             if event.end <= now:
    #                 if event.freq_id.id == 8:
    #                     await Scheduler.del_event()


def setup(bot):
    bot.add_cog(Scheduler(bot))
