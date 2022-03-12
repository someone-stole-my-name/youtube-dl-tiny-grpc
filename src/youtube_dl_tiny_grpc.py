#!/usr/bin/env python3
import argparse
import asyncio
import json
import logging
import os
import sys

import grpc
import youtube_dl
from google.protobuf.json_format import MessageToDict, ParseDict

import youtube_dl_tiny_grpc_pb2
import youtube_dl_tiny_grpc_pb2_grpc

# Coroutines to be invoked when the event loop is shutting down.
_cleanup_coroutines = []

class YoutubeDLServicer(youtube_dl_tiny_grpc_pb2_grpc.YoutubeDLServicer):
    """Provides methods that implement functionality of YoutubeDL server."""

    async def ExtractInfo(
        self,
        request: youtube_dl_tiny_grpc_pb2.ExtractInfoRequest,
        context: grpc.aio.ServicerContext
    ) -> youtube_dl_tiny_grpc_pb2.ExtractInfoResponse:

        if request.url == "" or not isinstance(request.url, str):
            context.set_details("Invalid URL")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            yield youtube_dl_tiny_grpc_pb2.ExtractInfoResponse()

        ydl_default_opts = {"verbose": True, "simulate": True}
        ydl_custom_opts = MessageToDict(request.options, including_default_value_fields=False, preserving_proto_field_name=True)
        ydl = youtube_dl.YoutubeDL({**ydl_default_opts, **ydl_custom_opts})

        info = ydl.extract_info(request.url, download=False)
        # FIXME: Yes, this is a hack. youtube_dl sometimes returns tuples for some repeated fields and ParseDict doesn't like that.
        info = json.loads(json.dumps(info))
        try:
            entries = info['entries'][0]['entries']
            for entry in entries:
                yield ParseDict(entry, youtube_dl_tiny_grpc_pb2.ExtractInfoResponse(), ignore_unknown_fields=True)
        except KeyError:
            try:
                entries = info['entries']
                for entry in entries:
                    yield ParseDict(entry, youtube_dl_tiny_grpc_pb2.ExtractInfoResponse(), ignore_unknown_fields=True)
            except:
                yield ParseDict(info, youtube_dl_tiny_grpc_pb2.ExtractInfoResponse(), ignore_unknown_fields=True)


async def serve(port: int, graceful_timeout: int = 30, enable_reflection: bool = False) -> None:
    """ Starts the gRPC server. """

    server = grpc.aio.server()
    youtube_dl_tiny_grpc_pb2_grpc.add_YoutubeDLServicer_to_server(
        YoutubeDLServicer(), server)

    if enable_reflection:
        from grpc_reflection.v1alpha import reflection
        reflection.enable_server_reflection((
            youtube_dl_tiny_grpc_pb2.DESCRIPTOR.services_by_name['YoutubeDL'].full_name,
            reflection.SERVICE_NAME,
        ), server)

    server.add_insecure_port(f"[::]:{port}")
    await server.start()

    async def server_graceful_shutdown():
        logging.info("Starting graceful shutdown...")
        await server.stop(graceful_timeout)

    _cleanup_coroutines.append(server_graceful_shutdown())
    await server.wait_for_termination()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default=os.environ.get('PORT'), type=int, help='Port to listen on')
    parser.add_argument('--graceful', default=30, type=int, help='Graceful shutdown timeout')
    parser.add_argument('--reflection', default=False, type=bool, help='Enables server reflection')
    args = parser.parse_args()
    if not args.port:
        sys.exit(parser.print_usage())

    logging.basicConfig()
    loop = asyncio.get_event_loop_policy().get_event_loop()
    try:
        loop.run_until_complete(serve(args.port, args.graceful, args.reflection))
    finally:
        loop.run_until_complete(*_cleanup_coroutines)
        loop.close()
