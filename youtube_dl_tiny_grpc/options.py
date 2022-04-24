import argparse
from multiprocessing import cpu_count
from os import environ

from setproctitle import getproctitle

from .util import guess_type
from .version import __version__

_COMPRESSION_ALGORITHMS = ["none", "deflate", "gzip"]
_DESCRIPTION = 'A tiny slice of youtube-dl exposed over gRPC'


def parse_opts(argv: list) -> argparse.Namespace:
    """ Parse command line options. """

    parser = argparse.ArgumentParser(
        description=_DESCRIPTION,
        prog=getproctitle(),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    prometheus = parser.add_argument_group("prometheus")

    prometheus.add_argument(
        '--prometheus-port',
        default=8080,
        type=int,
        help='Port to listen on',
    )

    prometheus.add_argument(
        '--prometheus-enable',
        action='store_true',
        help='Enable Prometheus metrics',
    )

    prometheus.add_argument(
        '--prometheus-directory',
        default="/tmp/youtube_dl_tiny_grpc_prometheus",
        type=str,
        help='Prometheus directory to share between processes',
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

    youtube_dl.add_argument(
        '--youtube-dl-proxy-list',
        default="",
        type=str,
        help="Comma separated list of proxies to use. \
        For example 'socks5://127.0.0.1:1080,http://127.0.0.1:8080'"
    )

    youtube_dl.add_argument(
        '--youtube-dl-cookies-file',
        default="",
        type=str,
        help="File to read cookies from and dump cookie jar in"
    )

    redis = parser.add_argument_group("redis")

    redis.add_argument(
        '--redis-enable',
        action='store_true',
        help='Enable Redis cache support',
    )

    redis.add_argument(
        '--redis-uri',
        type=str,
        default='redis://localhost:6379',
        help='Redis URI to connect to',
    )

    redis.add_argument(
        '--redis-ttl',
        type=int,
        default=3600,
        help='TTL for cached results',
    )

    general = parser.add_argument_group("general")

    general.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    general.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging',
    )

    general.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging',
    )

    args = parser.parse_args(argv)

    if args.verbose or args.debug or environ.get("DEBUG") is not None:
        print("configuration:")
        for arg in vars(args):
            print(f"  {arg}: {getattr(args, arg)}")

    return args
