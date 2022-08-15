# https://discord.com/api/oauth2/authorize?client_id=1008732377612292266&permissions=277025737792&scope=bot

import json
import os

import discord
import discord.ext.commands as commands
from discord import app_commands, HTTPException

import keep_alive

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!unused', intents=intents)
tree = bot.tree

# Default config
USER_TO_BLAME = 141243441614028800  # tameTNT#7902
BLAMING_GUILD = 1001090506140430406  # Durham University K-pop Society
MILESTONES = [10, 50, 100, 500, 1000]
CELEBRATE_GIF = 'https://media.giphy.com/media/IwAZ6dvvvaTtdI8SD5/giphy.gif'


def load_config_into_globals():
    with open('config.json', 'r+', encoding='utf-8') as fobj:
        f_cont = fobj.read()
        if f_cont:
            config = json.loads(f_cont)

            for key in config:
                globals()[key] = config[key]
        else:
            config = dict()
            config['USER_TO_BLAME'] = 141243441614028800  # tameTNT#7902
            config['BLAMING_GUILD'] = 1001090506140430406  # Durham University K-pop Society
            config['MILESTONES'] = [10, 50, 100, 500, 1000]
            config['CELEBRATE_GIF'] = 'https://media.giphy.com/media/IwAZ6dvvvaTtdI8SD5/giphy.gif'

        fobj.close()

    json.dump(config, open('config.json', 'w', encoding='utf-8'), indent=4)


def update_data(tracker: str, key: str, diff: int):
    if not isinstance(key, str):
        raise TypeError('key must be a string because JSON object keys must be strings')

    with open('data.json', 'r+', encoding='utf-8') as fobj:
        f_cont = fobj.read()
        if f_cont:
            data = json.loads(f_cont)
        else:
            data = dict()

        if tracker not in data:
            data[tracker] = dict()

        table = data[tracker]
        if key in table:
            table[key] += diff
        else:
            table[key] = diff

        new_val = table[key]

        fobj.close()

    json.dump(data, open('data.json', 'w', encoding='utf-8'), indent=4)

    return new_val


def play_the_blame(channel_id: int, user_id: int):
    update_data('by_channel', str(channel_id), 1)
    user_uses = update_data('by_user', str(user_id), 1)
    total_uses = update_data('total', 'total', 1)

    return user_uses, total_uses


def plural_s(i: int):
    if i == 1:
        return ''
    else:
        return 's'


@bot.event  # initial start-up event
async def on_ready():
    load_config_into_globals()

    await bot.change_presence(activity=discord.Game('the blame game'))
    await tree.sync(guild=discord.Object(id=BLAMING_GUILD))  # sync commands
    print('Bot ready & running - blame away...')

    # run a Flask server to allow for pinging from https://uptimerobot.com to keep repl.it running
    # and awake it from periodic sleep
    # https://todo.lucahuelle.repl.co/
    keep_alive.keep_alive()
    print('Bot and server both running')


@bot.event
async def on_message(message: discord.Message):
    # make sure bot has permission to see all messages

    if '#blameluca' in message.content.lower():
        loc = message.channel
        if isinstance(loc, discord.Thread):
            loc = loc.parent
        user_uses, total_uses = play_the_blame(loc.id, message.author.id)

        print('Luca blamed')
        is_self_blame = "\nWait, why blame yourself? :thinking:" if message.author.id == USER_TO_BLAME else ""
        await message.reply(
            content=f'<@{USER_TO_BLAME}> was blamed for something (most likely without justification).\n'
                    f"That makes it {total_uses} time{plural_s(total_uses)} that <@{USER_TO_BLAME}>'s been blamed... "
                    f'{user_uses} time{plural_s(user_uses)} by <@{message.author.id}> alone.{is_self_blame}'
        )

        if total_uses in MILESTONES:
            await loc.send(f"On the plus side at least, '#blameluca's been used {total_uses} "
                           f"time{plural_s(total_uses)} now\n{CELEBRATE_GIF}")


@tree.command(guild=discord.Object(id=BLAMING_GUILD))
@app_commands.describe(number='A number')
async def test(inter: discord.Interaction, number: int):
    """Test command"""
    await inter.response.send_message(f'{number=}', ephemeral=True)


if __name__ == '__main__':
    try:
        bot.run(os.environ['DISCORD_BLAME_TOKEN'])
    except HTTPException as e:
        print(f'{e}\nHTTP ERROR 429 - Too Many Requests\n'
              'Discord has rate limited repl.it and the bot will not work for this time.')
