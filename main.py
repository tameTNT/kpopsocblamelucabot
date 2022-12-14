# Invite: https://discord.com/api/oauth2/authorize?client_id=1008732377612292266&permissions=277025737792&scope=bot

import json
import os
import sqlite3
import typing as t
from datetime import datetime, timezone

import discord
from discord import app_commands


def console_log_with_time(msg: str, **kwargs):
    print(f'[blame] {datetime.now(tz=timezone.utc):%Y/%m/%d %H:%M:%S%f%z} - {msg}', **kwargs)


class BlameClient(discord.Client):
    def __init__(self, guild_id: int):
        intents = discord.Intents.default()
        intents.message_content = True  # allows seeking out #blameluca trigger
        intents.members = True  # enables accurate guild members cache
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.dev_guild_id = guild_id
        self.dev_sync_guild = discord.Object(id=self.dev_guild_id)
        console_log_with_time(f'Dev syncing to guild {self.dev_sync_guild.id}')

    async def setup_hook(self):
        # DEPLOY TODO: deploy = True
        deploy = False
        if deploy:
            self.tree.clear_commands(guild=self.dev_sync_guild)  # clear local commands
            await self.tree.sync(guild=self.dev_sync_guild)
            await self.tree.sync()  # global sync
            commands = await self.tree.fetch_commands()
        else:  # dev
            self.tree.copy_global_to(guild=self.dev_sync_guild)
            await self.tree.sync(guild=self.dev_sync_guild)
            commands = await self.tree.fetch_commands(guild=self.dev_sync_guild)

        console_log_with_time(f'Commands synced with {deploy=}.'
                              f'{" NB: Global commands may take an hour to appear." if deploy else ""}')
        for c in commands:
            console_log_with_time(f'Command ID {c.id} - "{c.name}" synced to Discord.')


# Default config
USER_TO_BLAME = 141243441614028800  # tameTNT#7902
BLAMING_GUILDS = [1001090506140430406]  # Just Durham University K-pop Society by default
MILESTONES = [10, 50, 100, 500, 1000]
CELEBRATE_GIF = 'https://media.giphy.com/media/IwAZ6dvvvaTtdI8SD5/giphy.gif'
DATA_FILE = 'blame/data.db'
SLOWMODE_TIME = 60
BONUS_QUIPS = {
    str(USER_TO_BLAME): 'Wait, why blame yourself tho? :thinking:'
}

CONFIG_PATH = 'blame/config.json'

client = BlameClient(BLAMING_GUILDS[0])


def load_config_into_globals(path=CONFIG_PATH):
    """Overwrites globals with values from config file at path (defaults to CONFIG_PATH)."""
    with open(path, 'r+', encoding='utf-8') as fobj:
        f_cont = fobj.read()
        if f_cont:
            config = json.loads(f_cont)

            for key, value in config.items():
                if key == 'MILESTONES':
                    value = sorted(value)

                globals()[key] = value
                config[key] = value  # for sorted milestones
        else:
            config = dict()
            config['USER_TO_BLAME'] = USER_TO_BLAME
            config['BLAMING_GUILDS'] = BLAMING_GUILDS
            config['MILESTONES'] = MILESTONES
            config['CELEBRATE_GIF'] = CELEBRATE_GIF
            config['DATA_FILE'] = DATA_FILE
            config['SLOWMODE_TIME'] = SLOWMODE_TIME
            config['BONUS_QUIPS'] = BONUS_QUIPS

        fobj.close()

    json.dump(config, open(path, 'w', encoding='utf-8'), indent=4)
    console_log_with_time('Config file loaded')


def update_config_with_global(global_name: str):
    config = json.load(open(CONFIG_PATH, 'r+', encoding='utf-8'))
    config[global_name] = globals()[global_name]
    json.dump(config, open(CONFIG_PATH, 'w', encoding='utf-8'), indent=4)
    console_log_with_time('Updated config file with globals')


class CursorCallable(t.Protocol):
    def __call__(self, db_cursor: sqlite3.Cursor = None, *args, **kwargs) -> t.Any: ...


def db_connect_wrapper(func: CursorCallable):
    """Wrapper handles opening database, creating main Blames table if it doesn't exist, and closing database."""

    def connect_to_db(*args, **kwargs):
        console_log_with_time('Opening database...')
        con = sqlite3.connect(DATA_FILE)
        cur = con.cursor()

        for guild_id in BLAMING_GUILDS:
            cur.execute(
                f'CREATE TABLE IF NOT EXISTS Blames_{guild_id} '
                '(blame_id INTEGER PRIMARY KEY AUTOINCREMENT, channel_id INTEGER, user_id INTEGER, timestamp INTEGER)'
            )

        func_result = func(*args, **kwargs, db_cursor=cur)

        con.commit()
        con.close()
        console_log_with_time('Database closed.')

        return func_result

    return connect_to_db


@db_connect_wrapper
def query_db(guild_id: int, query_type: t.Literal['channel_id', 'user_id', 'total', 'last'],
             q_argument: int = None, db_cursor: sqlite3.Cursor = None):
    console_log_with_time(f'Querying DB. Type: {query_type} | Arg: {q_argument}')
    if q_argument:
        if query_type in {'channel_id', 'user_id'}:
            return db_cursor.execute(
                f'SELECT COUNT(*) FROM Blames_{guild_id} WHERE {query_type} = ?', (q_argument,)
            ).fetchone()[0]
        elif query_type == 'last':  # returns most recent blame in table from user_id
            most_recent_blame = db_cursor.execute(
                f'SELECT timestamp FROM Blames_{guild_id} WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1',
                (q_argument,)
            ).fetchone()
            if most_recent_blame:
                return most_recent_blame[0]
            else:
                return 0
        else:
            raise ValueError('Missing argument for query_type.')

    elif query_type == 'total':  # counts all rows in table - i.e. total blames
        return db_cursor.execute(f'SELECT COUNT(*) FROM Blames_{guild_id}').fetchone()[0]
    else:
        raise ValueError('Invalid query_type.')


@db_connect_wrapper
def get_leaderboard_table(guild_id: int, tracker: t.Literal['channel_id', 'user_id'],
                          top: int, db_cursor: sqlite3.Cursor = None):
    """Returns the highest (the lowest if top < 0) scoring values for tracker."""
    if top < 0:
        top = -top
        sort_order = 'ASC'
    else:
        sort_order = 'DESC'
    lb_table = db_cursor.execute(f'SELECT {tracker}, COUNT(*) as c FROM Blames_{guild_id} '
                                 f'GROUP BY {tracker} ORDER BY c {sort_order} LIMIT {top}').fetchall()

    return lb_table


@db_connect_wrapper
def play_the_blame(guild_id: int, channel_id: int, user_id: int, db_cursor: sqlite3.Cursor = None):
    db_cursor.execute(
        f'INSERT INTO Blames_{guild_id} (channel_id, user_id, timestamp) VALUES (?, ?, ?)',
        (channel_id, user_id, int(datetime.utcnow().timestamp()))  # time is in UTC
    )

    user_uses = db_cursor.execute(
        f'SELECT COUNT(*) FROM Blames_{guild_id} WHERE user_id = ?', (user_id,)
    ).fetchone()[0]
    total_uses = db_cursor.execute(f'SELECT COUNT(*) FROM Blames_{guild_id}').fetchone()[0]

    console_log_with_time('Updated blame SQL table')
    return user_uses, total_uses


def plural_s(i: int):
    if i == 1:
        return ''
    else:
        return 's'


@client.event
async def on_message(message: discord.Message):
    # make sure bot has permission to see all message content and messages (in threads etc.)

    if '#blameluca' in message.content.lower():
        loc = message.channel
        if isinstance(loc, discord.Thread):
            loc = loc.parent

        current_blame_time = datetime.utcnow().timestamp()
        next_use_okay = query_db(loc.guild.id, 'last', message.author.id) + SLOWMODE_TIME
        if next_use_okay > current_blame_time:
            await message.reply(
                '<:ThisIsFine:1003384259882537040> Hold ya horses! '
                f'You can only blame {message.guild.get_member(USER_TO_BLAME).display_name} once every '
                f"{SLOWMODE_TIME} seconds. We wouldn't want anyone abusing this system, would we now?",
                delete_after=10
            )
            return

        user_uses, total_uses = play_the_blame(loc.guild.id, loc.id, message.author.id)

        console_log_with_time(f'Luca has been blamed at {current_blame_time:.1f} UTC '
                              f'by user {message.author.id} in channel {loc.id}')

        if (str_id := str(message.author.id)) in BONUS_QUIPS:
            quip_msg = f'\n{BONUS_QUIPS[str_id]}'
        else:
            quip_msg = ''

        await message.reply(
            content=f'<@{USER_TO_BLAME}> was blamed for something (most likely without justification).\n'
                    f"That makes it {total_uses} time{plural_s(total_uses)} that <@{USER_TO_BLAME}>'s been blamed... "
                    f'{user_uses} time{plural_s(user_uses)} by {message.author.mention} alone.{quip_msg}'
        )

        if total_uses in MILESTONES:
            await loc.send(f"On the plus side at least, <@{USER_TO_BLAME}>'s been blamed {total_uses} "
                           f'time{plural_s(total_uses)} in total now :unamused: \n{CELEBRATE_GIF}')
            console_log_with_time(f'Milestone ({total_uses}) reached!')


@client.tree.command()
@app_commands.describe(channel='Text channel to view blame stats for.',
                       user='Server member to view blame stats for.')
async def stats(inter: discord.Interaction, channel: t.Optional[discord.TextChannel],
                user: t.Optional[discord.Member]):
    """View the current stats for blaming. Can also display stats for a channel and/or user if desired."""

    console_log_with_time(f'Stats requested. '
                          f'Channel: {channel.id if channel else None} | User: {user.id if user else None}')
    response_embed = discord.Embed(
        title=':chart_with_upwards_trend: Blame stats',
        color=discord.Colour.blurple(),
        description=f'Total blames: {query_db(inter.guild_id, "total")}',
        timestamp=inter.created_at
    )

    if user:
        response_embed.add_field(
            name=':person_tipping_hand: Blames from user',
            value=f'{user.mention}: {query_db(inter.guild_id, "user_id", user.id)}',
            inline=True
        )

    if channel:
        response_embed.add_field(
            name=':closed_book: Blames in channel',
            value=f'{channel.mention}: {query_db(inter.guild_id, "channel_id", channel.id)}',
            inline=True
        )

    await inter.response.send_message(embed=response_embed)


@client.tree.command()
@app_commands.describe(category='Category to view leaderboard for.',
                       n='Leaderboard will show top n entries; bottom n entries if n is negative (<0).')
async def leaderboard(inter: discord.Interaction, category: t.Literal['users', 'channels'],
                      n: app_commands.Range[int, -10, 10]):
    """View the current leaderboard (i.e. the top/bottom n 'blamers') for a particular blaming category."""

    console_log_with_time(f'Leaderboard requested. Category: {category} | n: {n}')
    if category == 'users':
        lb_list = get_leaderboard_table(inter.guild_id, 'user_id', n)
        lb_list = map(lambda x: (inter.guild.get_member(x[0]).mention, x[1]), lb_list)
    elif category == 'channels':
        lb_list = get_leaderboard_table(inter.guild_id, 'channel_id', n)
        lb_list = map(lambda x: (inter.guild.get_channel(x[0]).mention, x[1]), lb_list)
    else:
        raise ValueError(f'Invalid category: {category}')
    lb_list = list(lb_list)

    leaderboard_embed = discord.Embed(
        title=f':100: Blame leaderboard - {category.title()} - {"Top" if n > 0 else "Bottom"} {abs(n)}',
        color=discord.Colour.blurple(),
        timestamp=inter.created_at
    )

    medal_map = {1: ':first_place:', 2: ':second_place:', 3: ':third_place:'}

    if lb_list:
        for i, (key, value) in enumerate(lb_list):
            leaderboard_embed.add_field(
                name=f'{medal_map[i + 1] if i < 3 and n > 0 else ""} {i + 1}.',
                value=f'{key}: {value} time{plural_s(value)}',
                inline=True
            )
    else:
        leaderboard_embed.add_field(
            name='<:BangchanShock:1004821030390480996> Wow no blames?',
            value="I'm sure that'll change soon enough..."
        )

    await inter.response.send_message(embed=leaderboard_embed)


@client.tree.command()
@app_commands.describe(n='Value to add as a milestone. '
                         'There will be a celebration when #blameluca has been used n times in total.')
@app_commands.checks.has_permissions(manage_guild=True)
async def milestones(inter: discord.Interaction, n: t.Optional[int]):
    """View milestones or adds n as a milestone to celebrate when #blameluca is used n times in total."""

    if n is None:
        await inter.response.send_message(
            content=f'Current milestones at: {", ".join(map(str, MILESTONES[:-1]))} and {MILESTONES[-1]} blames.'
        )
    else:
        if len(MILESTONES) > 50:
            await inter.response.send_message(content='Too many milestones! You can only have 50 milestones.')
        elif n not in MILESTONES:
            MILESTONES.append(n)
            update_config_with_global('MILESTONES')
            await inter.response.send_message(f"Added {n} as a milestone! Let's look forward to it~\n{CELEBRATE_GIF}")
            console_log_with_time(f'Milestones updated. {n} added.')
        else:
            await inter.response.send_message(f'{n} is already a milestone.')


@client.tree.command()
@app_commands.describe(user='Server member who deserves a special response when blaming Luca',
                       quip_msg='The message to add to the end of a #blameluca response.')
@app_commands.checks.has_permissions(manage_guild=True)
async def quip(inter: discord.Interaction, user: discord.Member, quip_msg: str):
    """Add or edit a special quip to add when a particular user uses #blameluca"""

    BONUS_QUIPS[str(user.id)] = quip_msg
    update_config_with_global('BONUS_QUIPS')
    await inter.response.send_message(f'Added "{quip_msg}" as a quip for {user.mention}')
    console_log_with_time(f'Quips updated. User: {user.id} | Quip: "{quip_msg}"')


@milestones.error
@quip.error
async def error_handler(inter: discord.Interaction, err: discord.app_commands.AppCommandError):
    console_log_with_time(f'Error occurred: {err!s}')
    if isinstance(err, discord.app_commands.CheckFailure):
        await inter.response.send_message(
            content="You don't have the necessary permissions to run this command - sorry :(",
            ephemeral=True
        )
    else:
        await inter.response.send_message(
            content=f'An error occurred: {err!s}\n #blameluca',
            ephemeral=False
        )


@client.event
async def on_ready():
    load_config_into_globals()

    await client.change_presence(activity=discord.Game('the blame game - #blameluca amir?'))

    console_log_with_time('Bot ready & running - blame away...')


@client.event
async def on_guild_join(guild: discord.Guild):
    BLAMING_GUILDS.append(guild.id)
    update_config_with_global('BLAMING_GUILDS')
    console_log_with_time(f'New guild joined: {guild.name} - {guild.id}')


@client.event
async def on_guild_remove(guild: discord.Guild):
    BLAMING_GUILDS.remove(guild.id)
    update_config_with_global('BLAMING_GUILDS')
    console_log_with_time(f'Guild removed from BLAMING_GUILDS: {guild.name} - {guild.id}')


# DEPLOY TODO: hardcode token
client.run(os.environ['DISCORD_BLAME_TOKEN'])
