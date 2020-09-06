************
twitch-radio
************
A simple Discord bot that plays audio from a Twitch stream

Requirements
############
Requires `ffmpeg<https://ffmpeg.org>`_.

Usage
#####
Simply call the bot with your Discord token:

.. code-block:: console
   twitch-radio TOKEN

Alternatively, the token can be read from the environment using ``DISCORD_BOT_TOKEN``:

.. clode-block:: console
   DISCORD_BOT_TOKEN=TOKEN twitch-radio

Commands
########

Use the ``!stream`` command to make the bot join your channel and start playing audio from a given channel:
::
   !stream asmongold
