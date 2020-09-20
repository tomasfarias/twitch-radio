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
    def __init__(self, source, *, url, volume=0.5):
        super().__init__(source, volume)

        self.url = url
        self.channel = Path(url).name

    @classmethod
    async def from_url(cls, url, loop=None):
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
    async def status(self, ctx, *, channel):
        """Reports Twitch channel status"""
        url = "twitch.tv/" + channel
        streams = session.streams(url)

        async with ctx.typing():
            if not streams:
                embed = discord.Embed(title="{} is OFFLINE".format(channel))
                await ctx.send(embed=embed)
            else:
                plugin = streams.popitem()[1].resolve_url(url)

                try:
                    stream = await self.bot.loop.run_in_executor(
                        None, lambda: plugin.api.streams(plugin._channel_id)
                    )

                except Exception:
                    logging.exception("Plugin or TwitchApi error when checking %s", url)
                    embed = discord.Embed(title="Error: failed to retrieve channel status")
                    await ctx.send(embed=embed)

                else:
                    embed = discord.Embed(
                        title="{} is LIVE".format(channel), description=stream["stream"]["channel"]["status"]
                    )
                    embed.add_field(name="Playing", value=stream["stream"]["game"])
                    await ctx.send(embed=embed)

    @commands.command()
    async def stream(self, ctx, *, channel):
        """Streams audio from a Twitch channel"""
        url = "twitch.tv/" + channel

        async with ctx.typing():
            try:
                player = await StreamlinkSource.from_url(url, loop=self.bot.loop)

            except (PluginError, KeyError):
                logging.exception("Fail to initialize StreamlinkSource from %s", url)
                embed = discord.Embed(title="Error: channel does not exist", description=channel)
                await ctx.send(embed=embed)

            else:
                ctx.voice_client.play(
                    player, after=lambda e: logging.error("Player error: %s" % e) if e else None
                )
                embed = discord.Embed(title="Now listening", description=channel)
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
