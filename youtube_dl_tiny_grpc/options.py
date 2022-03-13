import argparse

from setproctitle import getproctitle
from multiprocessing import cpu_count

from .version import __version__

from os import environ

from .util import (guessType)

_COMPRESSION_ALGORITHMS = ["none", "deflate", "gzip"]
_DESCRIPTION = 'A tiny slice of youtube-dl exposed over gRPC'


def parse_opts(argv: list) -> argparse.Namespace:
    """ Parse command line options. """

    parser = argparse.ArgumentParser(
        description=_DESCRIPTION,
        prog=getproctitle(),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    grpc = parser.add_argument_group("grpc")

    grpc.add_argument(
        '--grpc-port',
        default=50051,
        type=int,
        help='Port to listen on',
    )

    grpc.add_argument(
        '--grpc-graceful-shutdown-timeout',
        default=60,
        type=int,
        help='Graceful shutdown timeout',
    )

    grpc.add_argument(
        '--grpc-no-reflection',
        action='store_true',
        help='Disable gRPC server reflection',
    )

    grpc.add_argument(
        '--grpc-compression-algorithm',
        default='gzip',
        choices=_COMPRESSION_ALGORITHMS,
        help='Compression algorithm for the server',
    )

    youtube_dl = parser.add_argument_group("youtube-dl")

    youtube_dl.add_argument(
        '--youtube-dl-max-workers',
        default=cpu_count(),
        type=int,
        help='Max number of workers to use for youtube-dl',
    )

    youtube_dl.add_argument(
        '--youtube-dl-verbose',
        action='store_true',
        help='Verbose output for youtube-dl',
    )

    youtube_dl.add_argument(
        '--youtube-dl-no-quiet',
        action='store_false',
        help='Disable quiet output for youtube-dl',
    )

    general = parser.add_argument_group("general")

    general.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    general.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging',
    )

    args = parser.parse_args(argv)

    for action in parser._actions:
        action_name = action.option_strings[0].strip("--")
        if action_name.startswith((
            "grpc",
            "youtube-dl",
        )):
            env_var = action_name.upper().replace("-", "_")
            if environ.get(env_var) is not None:
                val = guessType(environ[env_var])
                if val is not None:
                    setattr(args, action_name.replace("-", "_"), val)
                else:
                    raise ValueError(f"Invalid value for {env_var}")

    if args.verbose:
        print("configuration:")
        for arg in vars(args):
            print(f"  {arg}: {getattr(args, arg)}")

    return args
