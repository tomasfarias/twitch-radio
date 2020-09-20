import asyncio
from pathlib import Path
import logging
import functools

import discord
from streamlink import Streamlink
from streamlink import PluginError

from discord.ext import commands


ffmpeg_options = {"options": "-vn"}

session = Streamlink()
session.set_option("hls-segment-threads", 3)
session.set_option("hls-segment-stream-data", True)


class StreamlinkSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, stream, url, volume=0.5):
        super().__init__(source, volume)

        self.url = url
        self.stream = stream
        self.channel = Path(url).name

    @classmethod
    async def from_url(cls, url, loop=None):
        loop = loop or asyncio.get_event_loop()
        stream = await loop.run_in_executor(None, lambda: session.streams(url)["audio_only"])

        return cls(discord.FFmpegPCMAudio(stream.url, **ffmpeg_options), stream=stream, url=url)

    async def get_status(self, loop=None):
        loop = loop or asyncio.get_event_loop()
        plugin = self.stream.session.resolve_url(self.url)
        status = await loop.run_in_executor(None, lambda: plugin.api.streams(plugin._channel_id))
        return status


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
    async def status(self, ctx, *, channel):
        """Reports Twitch channel status"""
        url = "twitch.tv/" + channel.strip()

        async with ctx.typing():
            try:
                plugin = session.streams(url).popitem()[1].session.resolve_url(url)

            except PluginError:
                # PluginError raised by plugin when Twitch Api timesout, means it is a non-existing channel
                embed = discord.Embed(title="Error: channel does not exist", description=channel)
                await ctx.send(embed=embed)
                return

            except KeyError:
                # KeyError raised by trying to index empty streams dictionary, means channel is offline
                # and not hosting anyone
                embed = discord.Embed(title="{} is OFFLINE".format(channel))
                await ctx.send(embed=embed)
                return

            try:
                status = await self.bot.loop.run_in_executor(
                    None, lambda: plugin.api.streams(plugin._channel_id)
                )

            except Exception:
                logging.exception("Plugin or TwitchApi error when checking %s", url)
                embed = discord.Embed(title="Error: failed to retrieve channel status")
                await ctx.send(embed=embed)

            else:
                embed = discord.Embed(
                    title="{} is LIVE".format(channel), description=status["stream"]["channel"]["status"]
                )
                embed.add_field(name="Playing", value=status["stream"]["game"])
                embed.set_thumbnail(url=status["stream"]["channel"]["logo"])
                await ctx.send(embed=embed)

    @commands.command()
    async def stream(self, ctx, *, channel):
        """Streams audio from a Twitch channel"""
        url = "twitch.tv/" + channel.strip()

        async with ctx.typing():
            try:
                player = await StreamlinkSource.from_url(url, loop=self.bot.loop)

            except PluginError:
                embed = discord.Embed(title="Error: channel does not exist", description=channel)
                await ctx.send(embed=embed)

            except KeyError:
                embed = discord.Embed(title="{} is OFFLINE".format(channel))
                await ctx.send(embed=embed)

            else:
                status = await player.get_status(loop=self.bot.loop)
                ctx.voice_client.play(
                    player, after=lambda e: logging.error("Player error: %s" % e) if e else None
                )
                embed = discord.Embed(title="Now listening", description=channel)
                embed.set_thumbnail(url=status["stream"]["channel"]["logo"])
                await ctx.send(embed=embed)

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
                embed = discord.Embed("Error: you are not connected to a voice channel")
                await ctx.send(embed=embed)
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!tr "),
    description="Simple Twitch audio streamer",
    help=commands.DefaultHelpCommand(),
)


@bot.event
async def on_ready():
    logging.info("Connected as %s", bot.user)
    await bot.change_presence(activity=discord.Activity(name="!tr help", type=discord.ActivityType.listening))


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None or after.channel == before.channel:
        return

    voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
    if voice_client is None or not voice_client.is_connected():
        return

    members = before.channel.members
    if len(members) == 1 and bot.user in members:
        await voice_client.disconnect()


bot.add_cog(Stream(bot))
