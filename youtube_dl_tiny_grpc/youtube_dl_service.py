from __future__ import annotations

import asyncio
import json

import grpc
from google.protobuf.json_format import MessageToDict, ParseDict
from youtube_dl import YoutubeDL

from .cache import Cache, gen_key
from .protobuf.youtube_dl_tiny_grpc_pb2 import (ExtractInfoRequest,
                                                ExtractInfoResponse)
from .protobuf.youtube_dl_tiny_grpc_pb2_grpc import \
    YoutubeDLServicer as YoutubeDLServerBase
from .util import ProcessPoolExecutor

import logging

# Offload all youtube_dl processing to a separate process in this pool
# Idea from https://github.com/grpc/grpc/issues/16001
_YOUTUBE_DL_PROCESS_POOL: ProcessPoolExecutor | None = None
_YOUTUBE_DL_DEFAULT_OPTS = {}
_YOUTUBE_DL_REDIS_URI: str | None = None

log = logging.getLogger(__name__)

def configure(
        default_opts: dict,
        process_pool: ProcessPoolExecutor, redis_uri: str | None) -> None:
    global _YOUTUBE_DL_DEFAULT_OPTS
    global _YOUTUBE_DL_PROCESS_POOL
    global _YOUTUBE_DL_REDIS_URI
    _YOUTUBE_DL_PROCESS_POOL = process_pool
    _YOUTUBE_DL_DEFAULT_OPTS = default_opts
    _YOUTUBE_DL_REDIS_URI = redis_uri


def shutdown_pool() -> None:
    global _YOUTUBE_DL_PROCESS_POOL
    log.info("stopping process pool")
    _YOUTUBE_DL_PROCESS_POOL.shutdown(False)


class YoutubeDLServer(YoutubeDLServerBase):
    """Provides methods that implement functionality of YoutubeDL server."""

    def __init__(self):
        log.info("Initializing!")
        self.cache = None
        if _YOUTUBE_DL_REDIS_URI is not None:
            self.cache = Cache(_YOUTUBE_DL_REDIS_URI)

    @staticmethod
    def _extract_info(url: str, opts: dict) -> dict:
        ydl = YoutubeDL(opts)
        info = ydl.extract_info(url, False)
        return info

    async def ExtractInfo(
            self,
            request: ExtractInfoRequest,
            context: grpc.aio.ServicerContext
    ) -> ExtractInfoResponse:
        if request.url == "" or not isinstance(request.url, str):
            context.set_details("Invalid URL")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            yield ExtractInfoResponse()

        ydl_custom_opts = MessageToDict(
                request.options,
                including_default_value_fields=False,
                preserving_proto_field_name=True
        )

        ydl_opts = {
            **_YOUTUBE_DL_DEFAULT_OPTS,
            **ydl_custom_opts,
            'simulate': True,
        }

        info = None
        if self.cache is not None:
            cached_ok = await self.cache.get(
                    await gen_key(request.url, json.dumps(ydl_opts))
            )
            if cached_ok:
                info = json.loads(cached_ok)

        if info is None:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                    _YOUTUBE_DL_PROCESS_POOL,
                    self._extract_info,
                    request.url,
                    ydl_opts)

            json_info = json.dumps(info)

            if self.cache is not None:
                await self.cache.set(
                        await gen_key(request.url, json.dumps(ydl_opts)),
                        json_info
                )

            # FIXME: Yes, this is a hack.
            # youtube_dl sometimes returns tuples for some repeated fields
            # and ParseDict doesn't like that.
            info = json.loads(json_info)

        try:
            entries = info['entries'][0]['entries']
            for entry in entries:
                yield ParseDict(
                        entry,
                        ExtractInfoResponse(),
                        ignore_unknown_fields=True)
        except KeyError:
            try:
                entries = info['entries']
                for entry in entries:
                    yield ParseDict(
                            entry,
                            ExtractInfoResponse(),
                            ignore_unknown_fields=True)
            except KeyError:
                yield ParseDict(
                        info,
                        ExtractInfoResponse(),
                        ignore_unknown_fields=True)
