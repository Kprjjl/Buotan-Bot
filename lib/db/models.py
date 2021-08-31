
class Guild:
    def __init__(self, guild_id, prefix, a_chnl_id):
        self.GuildID = guild_id
        self.Prefix = prefix
        self.a_chnlID = a_chnl_id


class Event:
    def __init__(self, event_id, guild_id, title, start, end, freq_id, desc):
        self.eventID = event_id
        self.guildID = guild_id
        self.title = title
        self.start = start
        self.end = end
        self.freqID = freq_id
        self.desc = desc


class Attendee:
    def __init__(self, discord_id, mention, name):
        self.discordID = discord_id,
        self.mention = mention
        self.name = name


class AnnouncementChannel:
    def __init__(self, guild_id, channel_id):
        self.guildID = guild_id
        self.channelID = channel_id


class PomodoroChannel:
    def __init__(self, guild_id, channel_id):
        self.guildID = guild_id
        self.channelID = channel_id


class WeightPreset:
    def __init__(self, hp, defense, atk, hp96, defense96, atk96, em, er, cr, cd):
        self.hp = hp
        self.defense = defense
        self.atk = atk
        self.hp96 = hp96
        self.defense96 = defense96
        self.atk96 = atk96
        self.em = em
        self.er = er
        self.cr = cr
        self.cd = cd

    def to_dict(self):
        return {
            'hp': self.hp,
            'def': self.defense,
            'atk': self.atk,
            'hp%': self.hp96,
            'def%': self.defense96,
            'atk%': self.atk96,
            'em': self.em,
            'er': self.er,
            'cr': self.cr,
            'cd': self.cd
        }

    @staticmethod
    def default():
        return WeightPreset(0, 0, 0.3, 0, 0, 0.5, 0.5, 0.5, 1, 1)


def objects_from_list(cls, list_of_tuple):
    return [cls(*item) for item in list_of_tuple]


def obj_from_record(cls, record):
    if record:
        return cls(*record)
    else:
        return None
