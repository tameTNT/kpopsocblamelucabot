# https://discord.com/api/oauth2/authorize?client_id=1008732377612292266&permissions=277025737792&scope=bot

import os

import discord
import discord.ext.commands as commands
from discord import app_commands, HTTPException

import keep_alive

# config constants
USER_TO_BLAME = 141243441614028800  # tameTNT#7902
BLAMING_GUILD = 1001090506140430406  # Durham University K-pop Society

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!unused', intents=intents)
tree = bot.tree


@bot.event  # initial start-up event
async def on_ready():
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
        print('Luca blamed')
        await message.reply(
            content=f'<@{USER_TO_BLAME}> was blamed for something (most likely without justification)'
        )


@tree.command(guild=discord.Object(id=BLAMING_GUILD))
@app_commands.describe(number='A number')
async def test(inter: discord.Interaction, number: int):
    """Test command"""
    await inter.response.send_message(f'{number=}', ephemeral=True)


try:
    bot.run(os.environ['DISCORD_BLAME_TOKEN'])
except HTTPException as e:
    print(f'{e}\nHTTP ERROR 429 - Too Many Requests\n'
          'Discord has rate limited repl.it and the bot will not work for this time.')
