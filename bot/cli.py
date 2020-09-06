import argparse
import typing
import os

from .bot import client


def run(args):
    parsed = parse_cli_args(args)
    client.run(parsed.token)


def parse_cli_args(args: typing.Sequence):
    parser = argparse.ArgumentParser(description="Stream Twitch audio into Discord")
    parser.add_argument(
        "token",
        help="Twitch bot token, can be read from TWITCH_TOKEN env",
        envvar="TWITCH_TOKEN",
        action=EnvDefault,
    )
    parser.add_argument("--debug", help="enable debug logging", default=False, action="store_true")

    parsed = parser.parse_args(args)
    return parsed


class EnvDefault(argparse.Action):
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if default is None and envvar is not None:
            default = os.getenv(envvar)
        if required is True and default is not None:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
