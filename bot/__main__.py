import typing
import sys

from .cli import run


def main(args: typing.Optional[typing.Sequence[str]]):
    if args is None:
        args = sys.argv[:1]
    cli.run(args)


if __name__ == '__main__':
    main()
