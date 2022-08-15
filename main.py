# https://discord.com/api/oauth2/authorize?client_id=1008732377612292266&permissions=277025737792&scope=bot

import os

import discord
from discord import HTTPException

import keep_alive

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)


@bot.event  # initial start-up event
async def on_ready():
    await bot.change_presence(activity=discord.Game('the blame game'))
    print('Bot ready & running - blame away...')

    # run a Flask server to allow for pinging from https://uptimerobot.com to keep repl.it running
    # and awake it from periodic sleep
    # https://###.lucahuelle.repl.co/
    keep_alive.keep_alive()
    print('Bot and server both running')


@bot.event
async def on_message(message: discord.Message):
    # make sure bot has permission to see all messages
    if '#blameluca' in message.content.lower():
        print('Luca blamed')
        await message.reply(
            content=f'<@141243441614028800> was blamed for something (most likely without justification)'
        )


try:
    bot.run(os.environ['DISCORD_BLAME_TOKEN'])
except HTTPException:
    print('HTTP ERROR 429 - Too Many Requests\n'
          'Discord has rate limited repl.it and the bot will not work for this time.')
