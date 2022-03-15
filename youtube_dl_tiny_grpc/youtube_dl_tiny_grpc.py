#!/usr/bin/env python3
import asyncio
import logging
import signal

import grpc

from .protobuf.youtube_dl_tiny_grpc_pb2_grpc import \
    add_YoutubeDLServicer_to_server as AddYoutubeDLServer
from .util import ProcessPoolExecutor
from .youtube_dl_service import YoutubeDLServer, \
    configure as configure_youtube_dl_server, \
    shutdown_pool as shutdown_youtube_dl_server

log = logging.getLogger(__name__)


class Server:
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

        redis = None
        if args['redis_enable']:
            redis = args['redis_uri']

        configure_youtube_dl_server(
                {
                    'verbose': args['youtube_dl_verbose'],
                    'quiet':   args['youtube_dl_no_quiet']
                },
                ProcessPoolExecutor(
                        max_workers=args['youtube_dl_max_workers']
                ),
                redis
        )

        self.grpc_graceful_shutdown_timeout = \
            args['grpc_graceful_shutdown_timeout']

        self.server = grpc.aio.server(
                compression=self.compression_algorithms[
                    args['grpc_compression_algorithm']
                ]
        )

        AddYoutubeDLServer(YoutubeDLServer(), self.server)

        if not args['grpc_no_reflection']:
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
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        log.info("starting graceful shutdown")
        self.not_in_shutdown = False

    async def shutdown(self) -> None:
        log.info("stopping server")
        await self.server.stop(self.grpc_graceful_shutdown_timeout)
        log.info("stopping youtube_dl process pool")
        shutdown_youtube_dl_server()
        log.info("waiting for server to stop")
        await self.server.wait_for_termination()

    async def run(self) -> None:
        # Start the gRPC server
        await self.server.start()

        log.info("server started")
        # Sleep until we get SIGINT or SIGTERM...etc
        while self.not_in_shutdown:
            await asyncio.sleep(5)
