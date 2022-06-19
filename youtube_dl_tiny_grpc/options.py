import argparse
from multiprocessing import cpu_count
import os

from setproctitle import getproctitle

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
        default=os.getenv("PROMETHEUS_PORT", 8080),
        type=int,
        help='Port to listen on',
    )

    prometheus.add_argument(
        '--prometheus-enable',
        default=os.getenv("PROMETHEUS_ENABLE", False),
        action='store_true',
        help='Enable Prometheus metrics',
    )

    prometheus.add_argument(
        '--prometheus-directory',
        default=os.getenv("PROMETHEUS_DIRECTORY", "/tmp/youtube_dl_tiny_grpc_prometheus"),
        type=str,
        help='Prometheus directory to share between processes',
    )

    grpc = parser.add_argument_group("grpc")

    grpc.add_argument(
        '--grpc-port',
        default=os.getenv("GRPC_PORT", 50051),
        type=int,
        help='Port to listen on',
    )

    grpc.add_argument(
        '--grpc-graceful-shutdown-timeout',
        default=os.getenv("GRPC_GRACEFUL_SHUTDOWN_TIMEOUT", 60),
        type=int,
        help='Graceful shutdown timeout',
    )

    grpc.add_argument(
        '--grpc-no-reflection',
        default=os.getenv("GRPC_NO_REFLECTION", False),
        help='Disable gRPC server reflection',
    )

    grpc.add_argument(
        '--grpc-compression-algorithm',
        default=os.getenv("GRPC_COMPRESSION_ALGORITHM", "gzip"),
        choices=_COMPRESSION_ALGORITHMS,
        help='Compression algorithm for the server',
    )

    youtube_dl = parser.add_argument_group("youtube-dl")

    youtube_dl.add_argument(
        '--youtube-dl-max-workers',
        default=os.getenv("YOUTUBE_DL_MAX_WORKERS", cpu_count()),
        type=int,
        help='Max number of workers to use for youtube-dl',
    )

    youtube_dl.add_argument(
        '--youtube-dl-verbose',
        default=os.getenv("YOUTUBE_DL_VERBOSE", False),
        action='store_true',
        help='Verbose output for youtube-dl',
    )

    youtube_dl.add_argument(
        '--youtube-dl-no-quiet',
        default=os.getenv("YOUTUBE_DL_NO_QUIET", True),
        action='store_false',
        help='Disable quiet output for youtube-dl',
    )

    youtube_dl.add_argument(
        '--youtube-dl-proxy-list',
        default=os.getenv("YOUTUBE_DL_PROXY_LIST", ""),
        type=str,
        help="Comma separated list of proxies to use. \
        For example 'socks5://127.0.0.1:1080,http://127.0.0.1:8080'"
    )

    youtube_dl.add_argument(
        '--youtube-dl-cookies-file',
        default=os.getenv("YOUTUBE_DL_COOKIES_FILE", ""),
        type=str,
        help="File to read cookies from and dump cookie jar in"
    )

    redis = parser.add_argument_group("redis")

    redis.add_argument(
        '--redis-enable',
        action='store_true',
        default=os.getenv("REDIS_ENABLE", False),
        help='Enable Redis cache support',
    )

    redis.add_argument(
        '--redis-uri',
        type=str,
        default=os.getenv("REDIS_URI", 'redis://localhost:6379'),
        help='Redis URI to connect to',
    )

    redis.add_argument(
        '--redis-ttl',
        type=int,
        default=os.getenv("REDIS_TTL", 3600),
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
        default=os.getenv("DEBUG", False),
        help='Enable debug logging',
    )

    general.add_argument(
        '--verbose',
        action='store_true',
        default=os.getenv("VERBOSE", False),
        help='Enable verbose logging',
    )

    args = parser.parse_args(argv)

    if args.verbose or args.debug is not None:
        print("configuration:")
        for arg in vars(args):
            print(f"  {arg}: {getattr(args, arg)}")

    return args
