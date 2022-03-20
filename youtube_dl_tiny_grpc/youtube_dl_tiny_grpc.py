#!/usr/bin/env python3
import asyncio
import logging
import signal

import grpc

from .protobuf.youtube_dl_tiny_grpc_pb2_grpc import \
    add_YoutubeDLServicer_to_server as AddYoutubeDLServer
from .util import ProcessPoolExecutor
from .cache import Cache
from .youtube_dl_service import YoutubeDLServer, \
    configure as configure_youtube_dl_server, \
    shutdown_pool as shutdown_youtube_dl_server

log = logging.getLogger(__name__)


class Server:
    """ YoutubeDL's gRPC Server """

    # Holds the shutdown method for the caller to call and clean up
    # eg: loop.run_until_complete(*server.cleanup)
    cleanup = []
    not_in_shutdown = True  # This triggers an ordered shutdown of the server
    compression_algorithms = {
        "none":    grpc.Compression.NoCompression,
        "deflate": grpc.Compression.Deflate,
        "gzip":    grpc.Compression.Gzip,
    }

    def __init__(self, args: dict):
        log.info("Initializing!")

        base_youtube_dl_args = {
            'verbose':   args['youtube_dl_verbose'] if "youtube_dl_verbose" in args else False,
            'quiet':     args['youtube_dl_no_quiet'] if "youtube_dl_no_quiet" in args else False,
            'simulate':  True,
            'call_home': False
        }

        if "youtube_dl_cookies_file" in args and \
                args['youtube_dl_cookies_file'] is not None and \
                args['youtube_dl_cookies_file'] != "":
            base_youtube_dl_args['cookiefile'] = \
                args['youtube_dl_cookies_file']

        redis = None
        if "redis_enable" in args and \
                args['redis_enable']:
            redis = Cache(args['redis_uri'], args['redis_ttl'])

        proxy_list = None
        if "youtube_dl_proxy_list" in args and args['youtube_dl_proxy_list'] is not None and \
                args['youtube_dl_proxy_list'] != "":
            proxy_list = args['youtube_dl_proxy_list'].split(',')

        configure_youtube_dl_server(
            base_youtube_dl_args,
            ProcessPoolExecutor(
                max_workers=args['youtube_dl_max_workers'] if "youtube_dl_max_workers" in args else 1
            ),
            redis,
            proxy_list
        )

        self.grpc_graceful_shutdown_timeout = \
            args['grpc_graceful_shutdown_timeout'] if "grpc_graceful_shutdown_timeout" in args else 0

        self.server = grpc.aio.server(
            compression=self.compression_algorithms[
                args['grpc_compression_algorithm'] if "grpc_compression_algorithm" in args else "none"
            ]
        )

        AddYoutubeDLServer(YoutubeDLServer(), self.server)

        if "grpc_no_reflection" in args and not args['grpc_no_reflection']:
            # pylint: disable=import-outside-toplevel
            from grpc_reflection.v1alpha import reflection

            from .protobuf.youtube_dl_tiny_grpc_pb2 import \
                DESCRIPTOR
            reflection.enable_server_reflection((
                DESCRIPTOR.services_by_name['YoutubeDL'].full_name,
                reflection.SERVICE_NAME,
            ), self.server)

        self.server.add_insecure_port(f"[::]:{args['grpc_port']}")

        # Add our method for the caller to clean up
        self.cleanup.append(self.shutdown())

        # Add signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._exit_gracefully)
        signal.signal(signal.SIGTERM, self._exit_gracefully)

    def _exit_gracefully(self, signum, frame):
        """ Internal method to exit gracefully on SIGINT or SIGTERM """
        if self.not_in_shutdown:
            log.info("starting graceful shutdown")
            self.not_in_shutdown = False

    async def shutdown(self) -> None:
        """ Shutdown the server """
        self._exit_gracefully(None, None)
        log.info("stopping server")
        await self.server.stop(self.grpc_graceful_shutdown_timeout)
        log.info("stopping youtube_dl process pool")
        shutdown_youtube_dl_server()
        log.info("waiting for server to stop")
        await self.server.wait_for_termination(self.grpc_graceful_shutdown_timeout)

    async def run(self) -> None:
        """ Run the server """
        await self.server.start()

        log.info("server started")
        # Sleep until we get SIGINT or SIGTERM...etc
        while self.not_in_shutdown:
            await asyncio.sleep(5)
