from discord.ext.commands import Cog
from discord.ext.commands import command
from discord import Embed
from datetime import datetime as dt
from datetime import time, timedelta
from sqlite3 import IntegrityError
from apscheduler.triggers.cron import CronTrigger
from typing import Union
from discord import Member, Role
from ..db import db
from ..db.models import *
from itertools import cycle

frequencies = {
    1: ({'sunday', 'sun', '1'}, 'Sunday'),
    2: ({'monday', 'mon', 'm', '2'}, 'Monday'),
    3: ({'tuesday', 'tue', 't',  '3'}, 'Tuesday'),
    4: ({'wednesday', 'wed', 'w',  '4'}, 'Wednesday'),
    5: ({'thursday', 'thu', 'th',  '5'}, 'Thursday'),
    6: ({'friday', 'fri', 'f',  '6'}, 'Friday'),
    7: ({'saturday', 'sat',  '7'}, 'Saturday'),
    8: ({'once', 'o', '8'}, 'Once')
}
days = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')


class Scheduler(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("scheduler")

    @command(aliases=['init_a_chnl'])
    async def init_announcement_chnl(self, ctx):
        guild = obj_from_record(Guild, db.record("SELECT * FROM guilds WHERE guildID = ?", ctx.guild.id))
        if guild:
            db.execute("UPDATE guilds SET announcementChannelID = ? WHERE GuildID = ?",
                       ctx.channel.id, ctx.guild.id)
            await ctx.send(f"Announcement channel for this server set to: {ctx.channel.mention}")

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

    @command()
    async def addevent(self, ctx, title, start=None, end=None, dates=None, freqs="once", *, desc="None"):
        none_equivs = {'', 'na', 'n/a', '.', None}

        def get_day(f):
            for valids, value in frequencies.values():
                if f in valids:
                    return value
            raise ValueError
        if freqs not in none_equivs:
            freq = ""
            for fr in freqs.split():
                try:
                    day = get_day(fr)
                    if day == "Once" and freq == "":
                        freq = "Once"
                    elif day == "Once" and freq != "":
                        return await ctx.send(f"Cannot assign other days and once at the same time to `freq`.")
                    else:
                        freq += f"{day} "
                except ValueError:
                    return await ctx.send(f"Invalid `freq` input.")
            freq = freq.strip()
        else:
            freq = "Once"
        # freq = freq.lower()
        # if freq not in frequencies[8][0]:
        #     freq_gen = (f for f in frequencies.values())
        #     while True:
        #         try:
        #             f = next(freq_gen)
        #             if freq in f[0] and f != frequencies[8]:
        #                 freq = f[1]
        #                 break
        #         except StopIteration:
        #             desc = freq + str(desc)
        #             freq = "Once"
        # else:
        #     freq = "Once"

        # freq becomes freqID
        if not (db.field("SELECT id FROM frequencies WHERE freq = ?", freq)):
            db.execute("INSERT INTO frequencies(freq) VALUES (?)", freq)
        freq = db.field("SELECT id FROM frequencies WHERE freq = ?", freq)

        time_fmt = ("%I:%M%p", "%I%p")
        date_fmt = ("%d-%m-%y", "%d-%m")
        now = dt.now().replace(second=0, microsecond=0)

        if start in none_equivs:
            start = now.time()
        else:
            start = Scheduler.fmt_datetime(start, time_fmt)
            if not start:
                return await ctx.send("Improper `start` input.")
            else:
                start = start.time()

        if end in none_equivs:
            end = time(0)  # tomorrow
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
                    if end == time(0):
                        e_date = s_date + timedelta(days=1)  # tomorrow
                    else:
                        e_date = s_date
                else:
                    s_date, e_date = dates.split("//")
                    if s_date in none_equivs:  #
                        s_date = now.date()
                    if s_date := Scheduler.fmt_datetime(s_date, date_fmt):
                        s_date = s_date.date()

                    temp_var = e_date
                    if e_date := Scheduler.fmt_datetime(e_date, date_fmt):
                        e_date = e_date.date()
                    else:
                        if temp_var in none_equivs:
                            e_date = s_date + timedelta(days=1)   # tomorrow
                        else:
                            raise ValueError
            except ValueError:
                return await ctx.send("Improper `dates` input")
        else:
            s_date = now.date()
            if end == time(0):
                e_date = s_date + timedelta(days=1)  # tomorrow
            else:
                e_date = s_date

        start = dt.combine(s_date, start)
        end = dt.combine(e_date, end)
        if start < end:
            # create event
            db.execute("INSERT INTO events(guildID, title,start,end,freqID,description) VALUES (?,?,?,?,?,?)",
                       ctx.guild.id, title, start, end, freq, desc)
            eventID = db.field("SELECT id FROM events WHERE title = ? AND guildID = ?", title, ctx.guild.id)
            return await ctx.send(f"New Event added with :id: `{eventID}`")
        else:
            return await ctx.send(f"start time must be earlier than end time.")

    @command()
    async def del_event(self, ctx, event_id):
        try:
            event_id = int(event_id)
            if not (title := db.field("SELECT title FROM events WHERE id = ? AND guildID = ?",
                                      int(event_id), ctx.guild.id)):
                return await ctx.send(f"Event with :id: `{event_id}` does not exist.")
        except ValueError:
            return await ctx.send("Improper `event_id` input.")
        else:
            db.execute("DELETE FROM events WHERE id = ?", event_id)
            return await ctx.send(f"Event: `{title}` deleted.")

    @command()
    async def events(self, ctx):
        events = objects_from_list(Event, db.records("SELECT * FROM events WHERE guildID = ?",
                                                     ctx.guild.id))
        if events:
            desc = ""
            for event in events:
                desc += f":id: `{event.eventID}` | {event.title}\n"
        else:
            desc = None

        embed = Embed(title="Registered Events:", description=desc, color=ctx.author.color)
        return await ctx.send(embed=embed)

    @command()
    async def event(self, ctx, event_id):
        try:
            event_id = int(event_id)
            if not (event := db.record("SELECT * FROM events WHERE id = ? AND guildID = ?",
                                       int(event_id), ctx.guild.id)):
                return await ctx.send(f"Event with :id: `{event_id}` does not exist.")
        except ValueError:
            return await ctx.send("Improper `event_id` input.")
        else:
            event = obj_from_record(Event, event)

        attendees = db.records(
            "SELECT attendees.* FROM attendees LEFT JOIN involvements ON discordID = attendeeID WHERE eventID = ?",
            event.eventID
        )
        if attendees:
            attendees = objects_from_list(Attendee, attendees)
            value = ""
            for attendee in attendees:
                value += f"`@{attendee.name}`, "
            value = value[:-2]
        else:
            value = None

        freq = db.field("SELECT freq FROM frequencies WHERE id = ?", event.freqID)
        desc = f"start: `{event.start.strftime('%I:%M%p %d-%m-%y %a')}`\n" \
               f"end: `{event.end.strftime('%I:%M%p %d-%m-%y %a')}`\n" \
               f"repeats: `{freq}`"
        embed = Embed(title=f"{event.title} | :id: `{event.eventID}`", description=desc)
        embed.add_field(inline=False, name="----------- Description: ------------",
                        value=event.desc)
        embed.add_field(inline=False,
                        name="----------- Participants: -----------",
                        value=value)
        return await ctx.send(embed=embed)

    @command()
    async def myevents(self, ctx, user_or_role: Union[Member, Role] = None):
        if user_or_role is None:
            discordID = ctx.author.id
        else:
            discordID = user_or_role.id
        events = db.records(
            "SELECT events.* FROM events LEFT JOIN involvements ON events.id = involvements.eventID "
            "WHERE attendeeID = ?",
            discordID
        )
        desc = f"**for `@{user_or_role.name}`:**\n"
        if events:
            events = objects_from_list(Event, events)
            for event in events:
                desc += f":id: `{event.eventID}` | {event.title}\n"
        else:
            desc += "None"
        embed = Embed(title="Registered Events:", description=desc, color=ctx.author.color)
        return await ctx.send(embed=embed)

    @command()
    async def participate(self, ctx, event_id, *, args=None):
        if args is None:
            attendees = [ctx.author]
        else:
            attendees = ctx.message.mentions + ctx.message.role_mentions
        # get event
        try:
            event_id = int(event_id)
            if not (eventID := db.field("SELECT id FROM events WHERE id = ?", event_id)):
                return await ctx.send(f"Event with :id: `{event_id}` does not exist.")
        except ValueError:
            return await ctx.send("Improper `event_id` input.")

        for attendee in attendees:
            try:
                db.execute("INSERT INTO attendees(discordID, mention, name) VALUES (?,?,?)",
                           attendee.id, attendee.mention, attendee.name)
            except IntegrityError:
                pass
            attendeeID = db.field("SELECT discordID FROM attendees WHERE discordID = ?", attendee.id)

            try:
                db.execute("INSERT INTO involvements(attendeeID, eventID) VALUES (?,?)",
                           attendeeID, eventID)
            except IntegrityError:
                continue
        return await ctx.send("Participation registered.")

    @command()
    async def remove_participation(self, ctx, event_id, *, args=None):
        if args is None:
            attendees = [ctx.author]
        else:
            attendees = ctx.message.mentions + ctx.message.role_mentions

        try:
            event_id = int(event_id)
            if not db.record("SELECT * FROM events WHERE id = ?", event_id):
                return await ctx.send(f"Event with :id: `{event_id}` does not exist.")
        except ValueError:
            return await ctx.send("Improper `event_id` input.")

        for attendee in attendees:
            if not (involvementID := db.field("SELECT id FROM involvements WHERE attendeeID = ? AND eventID = ?",
                                              attendee.id, event_id)):
                continue
            else:
                db.execute("DELETE FROM involvements WHERE id = ?", involvementID)

            if not (db.record("SELECT * FROM involvements WHERE attendeeID = ?", attendee.id)):
                db.execute("DELETE FROM attendees WHERE discordID = ?", attendee.id)

        return await ctx.message.add_reaction("\N{THUMBS UP SIGN}")

    @command(name="checkschedule", aliases=['checksched'])
    async def check_schedule(self, ctx):
        now = dt.now().replace(second=0, microsecond=0)
        events = db.records("SELECT * FROM events WHERE start <= ? AND end >= ?", now, now)
        if events:
            events = objects_from_list(Event, events)
            desc = ""
            for event in events:
                desc += f":id: `{event.eventID}` | **{event.title}**\n" \
                        f"------- `{event.start.strftime('%d-%m-%y')} - {event.end.strftime('%d-%m-%y')}`\n" \
                        f"-------- `{event.start.strftime('%I:%M%p')} - {event.end.strftime('%I:%M%p')}`\n"
        else:
            desc = None
        embed = Embed(title="Ongoing events:", description=desc)
        return await ctx.send(embed=embed)

    async def remind_event(self):
        no_diff = timedelta(0)
        remind_times = {
            timedelta(days=1): "tomorrow",
            timedelta(minutes=30): "in 30 minutes",
            timedelta(minutes=5): "in 5 minutes",
            no_diff: "event begins"
        }
        now = dt.now().replace(second=0, microsecond=0)
        a_channels = dict(db.records("SELECT GuildID, announcementChannelID "
                                     "FROM guilds WHERE announcementChannelID IS NOT NULL"))

        # -----START HANDLING------
        events = objects_from_list(Event, db.records(
            "SELECT events.* FROM events INNER JOIN guilds "
            "ON events.guildID = guilds.GuildID WHERE announcementChannelID IS NOT NULL AND events.start >= ?", now))
        # check if it is time to remind
        for event in events:
            if (diff := event.start - now) in remind_times:
                channel = self.bot.get_channel(a_channels[event.guildID])
                # send reminder
                if diff == timedelta(0):
                    message = f"**{event.title}** {remind_times[diff]}.\n"
                    attendees = db.records(
                        "SELECT attendees.* FROM attendees LEFT JOIN involvements "
                        "ON discordID = attendeeID WHERE eventID = ?", event.eventID
                    )
                    if attendees:
                        attendees = objects_from_list(Attendee, attendees)
                        for attendee in attendees:
                            message += f"{attendee.mention}, "
                        message = message[:-2]
                else:
                    message = f"**{event.title}** starts {remind_times[diff]}."
                await channel.send(message)

        # -----END HANDLING------
        events = objects_from_list(Event, db.records(
            "SELECT events.* FROM events INNER JOIN guilds "
            "ON events.guildID = guilds.GuildID WHERE announcementChannelID IS NOT NULL AND events.end <= ?", now))
        for event in events:
            if (now - event.end) == no_diff:
                channel = self.bot.get_channel(a_channels[event.guildID])

                if event.freqID == 8:  # Once
                    db.execute("DELETE FROM events WHERE id = ?", event.eventID)
                elif event.freqID < 8:
                    start = event.start + timedelta(days=7)
                    end = event.end + timedelta(days=7)
                    db.execute("UPDATE events SET start = ?, end = ? WHERE id = ?",
                               start, end, event.eventID)
                else:
                    freq = db.field("SELECT freq FROM frequencies WHERE id = ?", event.freqID)
                    day = now.strftime("%A")
                    freq = freq.split()
                    if freq.index(day) + 1 > len(freq) - 1:
                        nextday = freq[0]
                    else:
                        nextday = freq[freq.index(day) + 1]
                    cyc = cycle(days)
                    diff = 0
                    matched = False
                    while True:
                        d = next(cyc)
                        if d == day:
                            diff = 0
                            matched = True
                        else:
                            diff += 1
                        if d == nextday and matched:
                            break

                    start = event.start + timedelta(days=diff)
                    end = event.end + timedelta(days=diff)
                    db.execute("UPDATE events SET start = ?, end = ? WHERE id = ?",
                               start, end, event.eventID)

                await channel.send(f"**{event.title}** has ended.")


def setup(bot):
    dis_bot = Scheduler(bot)
    bot.add_cog(dis_bot)
    bot.scheduler.add_job(dis_bot.remind_event, CronTrigger(second=0))
