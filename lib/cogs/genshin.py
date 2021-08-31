from discord.ext.commands import Cog
from discord.ext.commands import command
from datetime import datetime as dt
from datetime import timedelta
from discord import Embed
from ..db.models import WeightPreset, obj_from_record
from ..db import db
from sqlite3 import IntegrityError

maxresin = 160  # max resins
rate = 8  # 1 resin per 8 mins
substat_values = {
    'hp': (209, 239, 418, 269, 478, 299, 538, 598),
    'def': (16, 19, 32, 21, 38, 23, 42, 46),
    'atk': (14, 16, 28, 18, 32, 19, 36, 38),
    'hp%': (4.1, 4.7, 8.2, 5.3, 9.4, 5.8, 10.6, 11.6),
    'def%': (5.1, 5.8, 10.2, 6.6, 11.6, 7.3, 13.2, 14.6),
    'atk%': (4.1, 4.7, 8.2, 5.3, 9.4, 5.8, 10.6, 11.6),
    'em': (16, 19, 32, 21, 38, 23, 42, 46),
    'er': (4.5, 5.2, 9, 5.8, 10.4, 6.5, 11.6, 13),
    'cr': (2.7, 3.1, 5.4, 3.5, 6.2, 3.9, 7, 7.8),
    'cd': (5.4, 6.2, 10.8, 7, 12.4, 7.8, 14, 15.6)
}


class Genshin(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("genshin")

    @command()
    async def resin(self, ctx, resin_count, *args):
        """
        Calculates how much time is required to reach resin stop points in `<args>`
        Example:
            `b!resin 3 20 40 80 160`
        """
        try:
            resin_count = int(resin_count)
            args = [int(a) for a in args]
        except ValueError:
            await ctx.send("Input integer only for <resin_count> and <resin-stops>.")

        if resin_count > maxresin:
            return await ctx.send(f"<resin_count> is beyond max resins ({maxresin}).")

        answers = []
        for stop in args:
            if (diff := stop - resin_count) >= 0:
                mins_left = timedelta(minutes=diff * rate)
                answer = dt.now() + mins_left
                answers.append(f"{stop} resins at {answer.strftime('%I:%M %p')}\n")
            else:
                answers.append(f"Already beyond {stop} resins.\n")

        desc = ""
        for a in answers:
            desc += a
        embed = Embed(description=desc)
        await ctx.send(embed=embed)

    @command()
    async def rate(self, ctx, preset="ADC", level: int = 0, *args):
        """
        Rates +0 and +4 artifact substats.
        `preset`: type "ADC" for default (**A**tk, phys/elem **D**mg bonus, **C**rit)
        `level`: accepts `0` or `4` only for +0 and +4 artifacts.
        `args`: ex: `cr:3.9 cd:7.8 atk%:5.8 em:23`
        """
        if level not in {0, 4}:
            return await ctx.send("Can only rate +0 or +4 artifacts.")

        # get preset weightings
        weightings = WeightPreset.default().to_dict()  # temporary
        if preset.lower() == 'adc':
            weightings = WeightPreset.default().to_dict()
        else:
            if not (weightings := db.record("SELECT * FROM weightPresets WHERE guildID = ? AND name = ?",
                                            ctx.guild.id, preset)):
                return await ctx.send("Preset does not exist.")
            weightings = WeightPreset(*weightings[3:]).to_dict()

        # get perfect score of weightings
        # top4 = sorted(list(weightings.items()), key=lambda e: e[1], reverse=True)
        weightings_list = sorted(list(weightings.values()), reverse=True)[:4]
        top4 = weightings_list[:4]
        bot4 = weightings_list[-1:5:-1]
        mid4 = top4[:2] + bot4[:2]
        # get perfect weighted points
        if level == 0:
            fullpoints = 6
        else:
            fullpoints = 8

        def weighted_score(weights, fpoints):
            s = 0
            for p in [fpoints * w for w in weights]:
                s += p
            return s
        perfect_score = weighted_score(top4, fullpoints)
        middle_score = weighted_score(mid4, fullpoints)
        trash_score = weighted_score(bot4, fullpoints)

        def point_value_gen(vals):
            for pts, v in enumerate(vals):
                yield pts, v

        score = 0
        for arg in args:
            try:
                sub, value = arg.split(":")
                value = float(value)
            except ValueError:
                return await ctx.send("Improper `<substat>:<value>` syntax or `<value>`.")
            else:
                sub = sub.lower()

            if values := substat_values.get(sub):
                gen = point_value_gen(values)
                while True:
                    try:
                        points, val = next(gen)
                    except StopIteration:
                        return await ctx.send(f"Unknown substat value: `{sub}:{value}`")
                    else:
                        if value == val:
                            score += (points + 1) * weightings[sub]
                            break
            else:
                return await ctx.send(f"Unknown substat: `{sub}`")
        rating = score/perfect_score * 100

        message = f"Substat Rating: {'{:.2f}'.format(rating)}%\n"
        if perfect_score >= score > (perfect_score + middle_score)/2:
            message += "**INVEST**"
        elif (perfect_score + middle_score)/2 >= score > middle_score:
            message += "Decent"
        elif middle_score >= score > (middle_score + trash_score)/2:
            message += "Eh."
        else:
            message += "**TRASH**"
        return await ctx.send(message)

    @command()
    async def preset(self, ctx, cmd, name=None, *args):
        """
        Weighting preset commands
        `cmd`: `all`/`add`/`del`/`select`
        `name`: prefix name (not needed for `all`)
        `args`: (for `add`) ex: `cr:1 cd:1 atk%:0.5 atk:0.3 em:0.5 er:0.5`
        """
        if cmd == 'all':
            presets = db.records("SELECT id, name FROM weightPresets WHERE guildID = ?", ctx.guild.id)
            desc = ""
            for ID, name in presets:
                desc += f":id: `{ID}` | {name}\n"
            embed = Embed(title="Presets:", description=desc)
            return await ctx.send(embed=embed)
        elif cmd == 'add':
            args = [a.split(":") for a in args]
            try:
                subs = ""
                vals = [ctx.guild.id, name]
                val_query = "?,?,"
                for sub, val in args:
                    sub = sub.lower()
                    sub = sub.replace("%", "96")
                    val = float(val)
                    if 1 >= val >= 0:
                        vals.append(val)
                        val_query += "?,"
                    else:
                        return await ctx.send("weighting value must be between 0 an 1.")
                    if sub.replace("96", "%") in substat_values.keys():
                        subs += f"{sub},"
                    else:
                        return await ctx.send(f"Unknown substat: `{sub}`")
                subs = subs[:-1]
                val_query = val_query[:-1]

                query = f"INSERT INTO weightPresets (guildID, name, {subs}) VALUES ({val_query})"
                db.execute(query, *vals)
                return await ctx.send("Preset registered.")
            except ValueError:
                return await ctx.send("value must be a number.")
            except IntegrityError:
                return await ctx.send("Name already exists.")

        elif cmd == 'del':
            if db.field("SELECT name FROM weightPresets WHERE guildID = ? AND name = ?", ctx.guild.id, name):
                db.execute("DELETE FROM weightPresets WHERE guildID = ? AND name = ?", ctx.guild, name)
                return await ctx.send(f"Preset `{name}` deleted.")
            else:
                return await ctx.send("No preset with that name.")
        elif cmd == 'select':
            if not (preset := db.record("SELECT * FROM weightPresets WHERE guildID = ? AND name = ?")):
                return await ctx.send("No preset with that name.")
            values = obj_from_record(WeightPreset, preset[3:])
            desc = ""
            for sub, val in values.to_dict():
                desc += f"`{sub}`: {val}\n"
            embed = Embed(title=f"`{preset[2]}` preset:", description=desc)
            return await ctx.send(embed=embed)
        else:
            return await ctx.send("`cmd` argument must be either `all`/`add`/`del`/`select`.")


def setup(bot):
    bot.add_cog(Genshin(bot))
