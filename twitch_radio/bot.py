import asyncio
from pathlib import Path
import logging

import discord
from streamlink import Streamlink

from discord.ext import commands


ffmpeg_options = {"options": "-vn"}

session = Streamlink()
session.set_option("hls-segment-threads", 3)
session.set_option("hls-segment-stream-data", True)


class StreamlinkSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, url, volume=0.5):
        super().__init__(source, volume)

        self.url = url
        self.channel = Path(url).name

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        stream = await loop.run_in_executor(None, lambda: session.streams(url)["audio_only"])

        return cls(discord.FFmpegPCMAudio(stream.url, **ffmpeg_options), url=url)


class Stream(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def stream(self, ctx, *, channel):
        """Streams audio from a Twitch channel"""
        url = "twitch.tv/" + channel
        async with ctx.typing():
            player = await StreamlinkSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print("Player error: %s" % e) if e else None)

        await ctx.send("Now listening to: {}".format(player.channel))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
        await ctx.voice_client.disconnect()

    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description="Simple Twitch audio streamer")


@bot.event
async def on_ready():
    logging.info("Connected as %s", bot.user)


bot.add_cog(Stream(bot))
