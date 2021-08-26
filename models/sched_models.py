import peewee as pw

db = pw.SqliteDatabase('db\scheduler.db', pragmas={'journal_mode': 'wal', 'foreign_keys': 1})


class BaseModel(pw.Model):
    class Meta:
        database = db


class Frequency(BaseModel):
    freq = pw.CharField(unique=True)


class Event(BaseModel):
    title = pw.CharField()
    start = pw.DateTimeField()
    end = pw.DateTimeField()
    freq_id = pw.ForeignKeyField(Frequency, backref="events")
    description = pw.CharField(null=True)


class Participant(BaseModel):
    discord_id = pw.IntegerField(primary_key=True)
    mention = pw.CharField()
    name = pw.CharField()


class Involvement(pw.Model):
    participant_id = pw.ForeignKeyField(Participant, backref="events")
    event_id = pw.ForeignKeyField(Event, backref="involved")

    class Meta:
        database = db
        indexes = (
            (('participant_id', 'event_id'), True),
        )


class AnnouncementChannel(BaseModel):
    guild_id = pw.IntegerField(primary_key=True)
    discord_id = pw.IntegerField()
