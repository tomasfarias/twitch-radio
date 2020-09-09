import argparse
import typing
import logging
import os

from .bot import bot


def run(args):
    parsed = parse_cli_args(args)
    logging.basicConfig(level=logging.DEBUG if parsed.debug is True else logging.INFO)
    bot.run(parsed.token)


def parse_cli_args(args: typing.Sequence):
    parser = argparse.ArgumentParser(description="Listen to Twitch audio in Discord")
    parser.add_argument(
        "token",
        help="Discord bot token, can be set via DISCORD_BOT_TOKEN environment variable",
        env_var="DISCORD_BOT_TOKEN",
        action=EnvDefault,
    )
    parser.add_argument("--debug", help="enable debug logging", default=False, action="store_true")

    parsed = parser.parse_args(args)
    return parsed


class EnvDefault(argparse.Action):
    def __init__(self, env_var, required=True, default=None, **kwargs):
        if default is None and env_var is not None:
            default = os.getenv(env_var)

        if required is True and default is not None:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
