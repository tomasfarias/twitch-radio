import logging

import discord

client = discord.Client()


@client.event
async def on_ready():
    logging.info("Logged in as %s", client.user)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!stream"):
        await message.channel.send("YAHALLO!")
